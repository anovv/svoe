import itertools
from typing import Dict, List, Any, Tuple, Optional


import ray
from ray import workflow
from ray.types import ObjectRef

from featurizer.features.data.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature, postorder
from featurizer.features.blocks.blocks import Block, BlockRange, BlockMeta, BlockRangeMeta, get_interval, DataParams
from portion import Interval, IntervalDict, closed
import pandas as pd
from streamz import Stream
import heapq
from utils.pandas.df_utils import load_df


# TODO move this to FeatureDefinition package
def build_stream_graph(feature: Feature) -> Dict[Feature, Stream]:
    stream_graph = {}

    def callback(feature: Feature):
        if feature.feature_definition.is_data_source():
            stream_graph[feature] = Stream()
            return
        dep_upstreams = {}
        for dep_feature in feature.children:
            dep_upstreams[dep_feature] = stream_graph[dep_feature]
        # TODO this should be part of Feature class
        stream = feature.feature_definition.stream(dep_upstreams, feature.params)
        stream_graph[feature] = stream

    postorder(feature, callback)
    return stream_graph


# TODO type hint
def get_overlaps(intervaled_values_per_feature: Dict[Feature, IntervalDict]) -> Dict:
    # TODO add visualization?
    # https://github.com/AlexandreDecan/portion
    # https://stackoverflow.com/questions/40367461/intersection-of-two-lists-of-ranges-in-python
    d = IntervalDict()
    first_feature = list(intervaled_values_per_feature.keys())[0]
    for interval, values in intervaled_values_per_feature[first_feature].items():
        d[interval] = {first_feature: values}  # named_intervaled_values_dict

    # join intervaled_values_dict for each feature_name with first to find all possible intersecting intervals
    # and their corresponding BlockRange/BlockRangeMeta objects
    for feature, intervaled_values_dict in intervaled_values_per_feature.items():
        if feature == first_feature:
            continue

        def concat(named_intervaled_values_dict, values):
            # TODO copy.deepcopy?
            res = named_intervaled_values_dict.copy()
            res[feature] = values
            return res

        combined = d.combine(intervaled_values_dict, how=concat)  # outer join
        d = combined[d.domain() & intervaled_values_dict.domain()]  # inner join

    # make sure all intervals are closed
    res = {}
    for interval, value in d.items():
        res[closed(interval.lower, interval.upper)] = value
    return res


# s3/data lake aux methods
# TODO move to separate class
# TODO add cpu/mem budget
@ray.remote
def load_if_needed(
    block_meta: BlockMeta,
) -> Block:
    # TODO if using Ray's Plasma, check shared obj store first, if empty - load from s3
    # TODO figure out how to split BlockRange -> Block and cache if needed
    # TODO sync keys
    return load_df(block_meta['path'])


# TODO for Virtual clock
# https://stackoverflow.com/questions/53829383/mocking-the-internal-clock-of-asyncio-event-loop
# aiotools Virtual Clock
# https://gist.github.com/damonjw/35aac361ca5d313ee9bf79e00261f4ea
# https://simpy.readthedocs.io/en/latest/
# https://github.com/salabim/salabim
# https://github.com/KlausPopp/Moddy
# https://towardsdatascience.com/object-oriented-discrete-event-simulation-with-simpy-53ad82f5f6e2
# https://towardsdatascience.com/simulating-real-life-events-in-python-with-simpy-619ffcdbf81f
# https://github.com/KarrLab/de_sim
# https://github.com/FuchsTom/ProdSim
# https://github.com/topics/discrete-event-simulation?l=python&o=desc&s=forks
# https://docs.python.org/3/library/tkinter.html
# TODO this should be in Feature class
@ray.remote
def calculate_feature(
    feature: Feature,
    dep_refs: Dict[Feature, List[ObjectRef[Block]]], # maps dep feature to BlockRange # TODO List[BlockRange] when using 'holes'
    interval: Interval
) -> Block:
    # TODO add mem tracking
    # this loads blocks for all dep features from shared object store to workers heap
    # hence we need to reserve a lot of mem here
    dep_features = list(dep_refs.keys())
    dep_block_refs = list(dep_refs.values())
    all_block_refs = list(itertools.chain(dep_block_refs))
    all_objs = ray.get(*all_block_refs)
    start = 0
    deps = {}
    for i in range(len(dep_features)):
        dep_feature = dep_features[i]
        dep_blocks = all_objs[start: start + len(dep_block_refs[i])]
        deps[dep_feature] = dep_blocks
        start = start + len(dep_block_refs[i])

    merged = merge_blocks(deps)
    # construct upstreams
    upstreams = {dep_named_feature: Stream() for dep_named_feature in deps.keys()}
    out_stream = feature.feature_definition.stream(upstreams, feature.params)
    return run_stream(merged, upstreams, out_stream, interval)


# TODO util this
# TODO we assume no 'holes' here
def merge_blocks(
    blocks: Dict[Feature, BlockRange]
) -> List[Tuple[Feature, Event]]:
    # TODO we assume no 'hoes' here
    # merge
    merged = None
    features = list(blocks.keys())
    for i in range(0, len(features)):
        feature = features[i]
        block_range = blocks[feature]
        named_events = []
        for block in block_range:
            parsed = feature.feature_definition.parse_events(block)
            named = []
            for e in parsed:
                named.append((feature, e))
            named_events.extend(named)
        # TODO check if events are timestamp sorted?
        if i == 0:
            merged = named_events
        else:
            # TODO explore heapdict
            merged = heapq.merge(merged, named_events, key=lambda named_event: named_event[1]['timestamp'])

    return merged


# TODO util this
def run_stream(
    named_events: List[Tuple[Feature, Event]],
    sources: Dict[Feature, Stream],
    out: Stream,
    interval: Optional[Interval] = None
) -> Block:
    res = []

    # TODO make it a Streamz object?
    def append(elem: Any):
        # if interval is not specified, append everything
        if interval is None:
            res.append(elem)
            return

        # if interval is specified, append only if timestamp is within the interval
        if interval.lower <= elem['timestamp'] <= interval.upper:
            res.append(elem)

    out.sink(append)

    # TODO time this
    for named_event in named_events:
        feature = named_event[0]
        sources[feature].emit(named_event[1])

    return pd.DataFrame(res)  # TODO set column names properly, using FeatureDefinition schema method?


def _interval_meta(interval: Interval) -> BlockMeta:
    return {
        'start_ts': interval.lower,
        'end_ts': interval.upper,
    }


# graph construction
# TODO make 3d visualization with networkx/graphviz
def build_feature_task_graph(
    dag: Dict, # DAGNode per feature per range
    feature: Feature,
    # TODO decouple derived feature_ranges_meta and input data ranges meta
    ranges_meta: Dict[Feature, List]  # TODO typehint when decide on BlockRangeMeta/BlockMeta
):
    # TODO pass this as a param

    # bottom up/postorder traversal
    def tree_traversal_callback(feature: Feature):
        if feature.feature_definition.is_data_source():
            # leaves
            # TODO decouple derived feature_ranges_meta and input data ranges meta
            ranges = ranges_meta[feature]  # this is already populated for Data in load_data_ranges above
            for block_meta in ranges:
                # TODO we assume no 'holes' in data here
                interval = get_interval(block_meta)
                if feature not in dag:
                    dag[feature] = {}
                node = load_if_needed.bind(block_meta)

                # TODO check if duplicate feature/interval
                dag[feature][interval] = node
            return

        grouped_ranges_by_dep_feature = {}
        for dep_feature in feature.children:
            dep_ranges = ranges_meta[dep_feature]
            # TODO this should be in Feature class
            grouped_ranges_by_dep_feature[dep_feature] = feature.feature_definition.group_dep_ranges(dep_ranges, feature, dep_feature)

        overlaps = get_overlaps(grouped_ranges_by_dep_feature)
        ranges = []
        for interval, overlap in overlaps.items():
            # TODO add size_kb/memory_size_kb to proper size memory usage for aggregate tasks downstream
            result_meta = _interval_meta(interval)
            ranges.append(result_meta)
            if feature not in dag:
                dag[feature] = {}

            # TODO use overlap to fetch results of dep delayed funcs
            dep_nodes = {}
            for dep_feature in overlap:
                ds = []
                for dep_block_meta in overlap[dep_feature]:
                    dep_interval = get_interval(dep_block_meta)
                    dep_node = dag[dep_feature][dep_interval]
                    ds.append(dep_node)
                dep_nodes[dep_feature] = ds
            node = calculate_feature.bind(feature, dep_nodes, interval)

            # TODO check if duplicate feature/interval
            dag[feature][interval] = node

        # TODO check if duplicate feature
        ranges_meta[feature] = ranges

    postorder(feature, tree_traversal_callback)

    return dag


def execute_task_graph(dag: Dict, feature: Feature) -> List[Block]:
    root_nodes = list(dag[feature].values())
    workflow_results_refs = []
    with ray.init(address='auto'):
        # TODO launch single workflow for this?
        for node in root_nodes:
            r = workflow.run_async(node)
            workflow_results_refs.append(r)

        return ray.get(workflow_results_refs)


def _build_feature_set_task_graph(
    dag: Dict,
    features: List[Feature],
    ranges_meta: Dict[Feature, List]
):
    for feature in features:
        # TODO check if feature is already in dag and skip?
        dag = build_feature_task_graph(dag, feature, ranges_meta)

    return dag


def _point_in_time_join(dag: Dict) -> Tuple[List, Dict]:
    # TODO can we use IntervalDict directly in dag?
    nodes_per_feature_per_interval = {}
    for feature in dag:
        nodes_per_interval = IntervalDict()
        for interval in dag[feature]:
            nodes_per_interval[interval] = dag[feature][interval]
        nodes_per_feature_per_interval[feature] = nodes_per_interval

    overlaps = get_overlaps(nodes_per_feature_per_interval)

    joined_nodes = []
    for overlap, nodes in overlaps:
        # TODO set resource spec here
        join_node = _point_in_time_join_block.bind(overlap, nodes)
        joined_nodes.append(join_node)

    # TODO make sure nodes are time sorted so we can streamline execution
    return joined_nodes, dag


@ray.remote
def _point_in_time_join_block(interval: Interval, blocks_refs: List[ObjectRef[Block]]):
    # TODO
    return


def build_feature_label_set_task_graph(
    dag: Dict,
    features: List[Feature],
    label: Feature,
    label_lookahead: str = '1m',
):
    return


