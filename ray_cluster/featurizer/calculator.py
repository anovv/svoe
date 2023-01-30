from typing import Union, Dict, Callable, Type, List, OrderedDict, Any, Tuple, Optional
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data_definition import DataDefinition, Event
from featurizer.features.feature_tree.feature_tree import FeatureTreeNode, postorder
from featurizer.features.blocks.blocks import Block, BlockRange, BlockMeta, BlockRangeMeta, get_interval, DataParams
import dask.graph_manipulation
from portion import Interval, IntervalDict, closed
import pandas as pd
from streamz import Stream
import heapq
from featurizer.features.loader.df_utils import load_single_file


# TODO move this to FeatureDefinition package
def build_stream_graph(feature: FeatureTreeNode) -> Dict[FeatureTreeNode, Stream]:
    stream_graph = {}

    def callback(feature: FeatureTreeNode):
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


def load_data_ranges(
    feature_definition: Type[FeatureDefinition],
    data_params: DataParams,
    start_date: str = None,
    end_date: str = None
) -> Dict:
    # TODO call data catalog service
    return {}


# TODO type hint
def get_ranges_overlaps(grouped_ranges: Dict[FeatureTreeNode, IntervalDict]) -> Dict:
    # TODO add visualization?
    # https://github.com/AlexandreDecan/portion
    # https://stackoverflow.com/questions/40367461/intersection-of-two-lists-of-ranges-in-python
    d = IntervalDict()
    first_feature = list(grouped_ranges.keys())[0]
    for interval, ranges in grouped_ranges[first_feature].items():
        d[interval] = {first_feature: ranges}  # named_ranges_dict

    # join ranges_dict for each feature_name with first to find all possible intersecting intervals
    # and their corresponding BlockRange/BlockRangeMeta objects
    for feature, ranges_dict in grouped_ranges.items():
        if feature == first_feature:
            continue

        def concat(named_ranges_dict, ranges):
            res = named_ranges_dict.copy()
            res[feature] = ranges
            return res

        combined = d.combine(ranges_dict, how=concat)  # outer join
        d = combined[d.domain() & ranges_dict.domain()]  # inner join

    # make sure all intervals are closed
    res = {}
    for interval, value in d.items():
        res[closed(interval.lower, interval.upper)] = value
    return res


# s3/data lake aux methods
# TODO move to separate class
# TODO add cpu/mem budget
@dask.delayed
def load_if_needed(
    block_meta: BlockMeta,
) -> Block:
    # TODO if using Ray's Plasma, check shared obj store first, if empty - load from s3
    # TODO figure out how to split BlockRange -> Block and cache if needed
    # TODO sync keys
    return load_single_file(block_meta['path'])


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
@dask.delayed
def calculate_feature(
    feature: FeatureTreeNode,
    dep_feature_results: Dict[FeatureTreeNode, BlockRange], # maps dep feature to BlockRange # TODO List[BlockRange] when using 'holes'
    interval: Interval
) -> Block:
    merged = merge_feature_blocks(dep_feature_results)
    # construct upstreams
    upstreams = {dep_named_feature: Stream() for dep_named_feature in dep_feature_results.keys()}
    out_stream = feature.feature_definition.stream(upstreams, feature.params)
    return run_stream(merged, upstreams, out_stream, interval)


# TODO util this
# TODO we assume no 'holes' here
def merge_feature_blocks(
    feature_blocks: Dict[FeatureTreeNode, BlockRange]
) -> List[Tuple[FeatureTreeNode, Event]]:
    # TODO we assume no 'hoes' here
    # merge
    merged = None
    features = list(feature_blocks.keys())
    for i in range(0, len(features)):
        feature = features[i]
        block_range = feature_blocks[feature]
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
            merged = heapq.merge(merged, named_events, key=lambda named_event: named_event[1]['timestamp'])

    return merged


# TODO util this
def run_stream(
    named_events: List[Tuple[FeatureTreeNode, Event]],
    sources: Dict[FeatureTreeNode, Stream],
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


# TODO should be FeatureDefinition/Feature method
def calculate_feature_meta(
    feature: FeatureTreeNode,
    dep_feature_results: Dict[FeatureTreeNode, BlockRangeMeta],
    # maps dep feature to BlockRange # TODO List[BlockRangeMeta]?
    interval: Interval
) -> BlockMeta:
    return {
        'start_ts': interval.lower,
        'end_ts': interval.upper,
    }


# graph construction
# TODO make 3d visualization with networkx/graphviz
def build_task_graph(
    feature: FeatureTreeNode,
    # TODO decouple derived feature_ranges_meta and input data ranges meta
    feature_ranges_meta: Dict[FeatureTreeNode, List]  # TODO typehint when decide on BlockRangeMeta/BlockMeta
):
    feature_delayed_funcs = {}  # feature delayed functions per range per feature

    # bottom up/postorder traversal
    def tree_traversal_callback(feature: FeatureTreeNode):
        if feature.feature_definition.is_data_source():
            # leaves
            # TODO decouple derived feature_ranges_meta and input data ranges meta
            ranges = feature_ranges_meta[feature]  # this is already populated for Data in load_data_ranges above
            for block_meta in ranges:
                # TODO we assume no 'holes' in data here
                interval = get_interval(block_meta)
                if feature not in feature_delayed_funcs:
                    feature_delayed_funcs[feature] = {}
                feature_delayed = load_if_needed(block_meta)
                feature_delayed_funcs[feature][interval] = feature_delayed
            return

        grouped_ranges_by_dep_feature = {}
        for dep_feature in feature.children:
            dep_ranges = feature_ranges_meta[dep_feature]
            # TODO this should be in Feature class
            grouped_ranges_by_dep_feature[dep_feature] = feature.feature_definition.group_dep_ranges(dep_ranges, feature, dep_feature)

        overlaps = get_ranges_overlaps(grouped_ranges_by_dep_feature)
        ranges = []
        for interval, overlap in overlaps.items():
            # TODO is this needed? is it for block or range ?
            result_meta = calculate_feature_meta(feature, overlap, interval)
            ranges.append(result_meta)
            if feature not in feature_delayed_funcs:
                feature_delayed_funcs[feature] = {}

            # TODO use overlap to fetch results of dep delayed funcs
            dep_delayed_funcs = {}
            for dep_named_feature in overlap:
                ds = []
                for dep_block_meta in overlap[dep_named_feature]:
                    dep_interval = get_interval(dep_block_meta)
                    dep_delayed_func = feature_delayed_funcs[dep_named_feature][dep_interval]
                    ds.append(dep_delayed_func)
                dep_delayed_funcs[dep_named_feature] = ds
            feature_delayed = calculate_feature(feature, dep_delayed_funcs, interval)
            feature_delayed_funcs[feature][interval] = feature_delayed

        feature_ranges_meta[feature] = ranges

    postorder(feature, tree_traversal_callback)
    # list of root feature delayed funcs for all ranges
    return list(feature_delayed_funcs[feature].values())
