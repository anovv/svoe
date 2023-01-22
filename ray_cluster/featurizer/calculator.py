from typing import Union, Dict, Callable, Type, List, OrderedDict, Any, Tuple, Optional
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data_definition import NamedFeature, DataDefinition
from featurizer.features.blocks.blocks import Block, BlockRange, BlockMeta, BlockRangeMeta, get_interval, DataParams
import dask.graph_manipulation
from portion import Interval, IntervalDict
import pandas as pd
from streamz import Stream
import heapq
from featurizer.features.loader.df_utils import load_single_file


# TODO util this
def postorder(named_feature_node: NamedFeature, callback: Callable):
    fd_type = named_feature_node[1]
    if fd_type.is_data_source():
        callback(named_feature_node)
        return
    named_children = fd_type.dep_upstream_schema_named()
    for dep_named_feature in named_children:
        postorder(dep_named_feature, callback)

    callback(named_feature_node)


# TODO move this to FeatureDefinition package
def build_stream_graph(named_feature: NamedFeature) -> Dict[NamedFeature, Stream]:
    stream_graph = {}

    def callback(named_feature: NamedFeature):
        fd_type = named_feature[1]
        if fd_type.is_data_source():
            stream_graph[named_feature] = Stream()
            return
        dep_upstreams = {}
        named_children = fd_type.dep_upstream_schema_named()
        for dep_named_feature in named_children:
            dep_upstreams[dep_named_feature[0]] = stream_graph[dep_named_feature]
        stream = fd_type.stream(dep_upstreams)
        stream_graph[named_feature] = stream

    postorder(named_feature, callback)
    return stream_graph


def load_data_ranges(
    fd_type: Type[FeatureDefinition],
    data_params: DataParams,
    start_date: str = None,
    end_date: str = None
) -> Dict:
    # TODO call data catalog service
    return {}


# TODO make IntervalDict support generics to indicate value type hints
def get_ranges_overlaps(grouped_ranges: Dict[NamedFeature, IntervalDict]) -> IntervalDict:
    # TODO add visualization?
    # https://github.com/AlexandreDecan/portion
    # https://stackoverflow.com/questions/40367461/intersection-of-two-lists-of-ranges-in-python
    d = IntervalDict()
    first_named_feature = list(grouped_ranges.keys())[0]
    for interval, ranges in grouped_ranges[first_named_feature].items():
        d[interval] = {first_named_feature: ranges}  # named_ranges_dict

    # join ranges_dict for each feature_name with first to find all possible intersecting intervals
    # and their corresponding BlockRange/BlockRangeMeta objects
    for named_feature, ranges_dict in grouped_ranges.items():
        # compare by names
        if named_feature[0] == first_named_feature[0]:
            continue

        def concat(named_ranges_dict, ranges):
            res = named_ranges_dict.copy()
            res[named_feature] = ranges
            return res

        combined = d.combine(ranges_dict, how=concat)  # outer join
        d = combined[d.domain() & ranges_dict.domain()]  # inner join

    return d


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
@dask.delayed
def calculate_feature(
    fd_type: Type[FeatureDefinition],
    dep_feature_results: Dict[NamedFeature, BlockRange], # maps dep feature to BlockRange # TODO List[BlockRange] when using 'holes'
    interval: Interval
) -> Block:
    merged = merge_feature_blocks(dep_feature_results)
    # construct upstreams
    upstreams = {dep_named_feature[0]: Stream() for dep_named_feature in dep_feature_results.keys()}
    out_stream = fd_type.stream(upstreams)
    return run_stream(merged, upstreams, out_stream, interval)


# TODO util this
# TODO we assume no 'holes' here
# TODO typehint Event = Dict[str, Any] ? note that this corresponds to grouped events by timestamp
def merge_feature_blocks(
    feature_blocks: Dict[NamedFeature, BlockRange]
) -> List[Dict[str, Any]]:
    # TODO we assume no 'hoes' here
    # merge
    merged = None
    named_features = list(feature_blocks.keys())
    for i in range(0, len(named_features)):
        named_feature = named_features[i]
        block_range = feature_blocks[named_feature]
        events = []
        for block in block_range:
            parsed = named_feature[1].parse_events(block, named_feature[0])
            events.extend(parsed)
        # TODO check if events are timestamp sorted?
        if i == 0:
            merged = events
        else:
            merged = heapq.merge(merged, events, key=lambda e: e['timestamp'])

    return merged


# TODO util this
def run_stream(
    events: List[Any],
    # events: List[Dict[str, Any]],
    sources: Dict[str, Stream],
    out: Stream,
    interval: Optional[Interval]=None
) -> pd.DataFrame: # TODO Block?
    res = []

    # TODO make it a Streamz object?
    def append(elem: Any):
        # if interval is not specified, append everything
        if interval is None:
            res.append(elem)
            return

        # if interval is specified, append only if timestamp is within the interval
        if interval.lower <= elem.timestamp <= interval.upper:
            res.append(elem)

    out.sink(append)

    # TODO time this
    for event in events:
        dep_feature_name = event.feature_name
        sources[dep_feature_name].emit(event)

    return pd.DataFrame(res)  # TODO set column names properly, using FeatureDefinition schema method?


# TODO should be FeatureDefinition method
def calculate_feature_meta(
    fd_type: Type[FeatureDefinition],
    dep_feature_results: Dict[NamedFeature, BlockRangeMeta],
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
    named_root_feature: NamedFeature,
    feature_ranges_meta: Dict[NamedFeature, List]  # TODO typehint when decide on BlockRangeMeta/BlockMeta
):
    feature_delayed_funcs = {}  # feature delayed functions per range per feature

    # bottom up/postorder traversal
    def tree_traversal_callback(named_feature: NamedFeature):
        fd_type = named_feature[1]
        if fd_type.is_data_source():
            # leaves
            ranges = feature_ranges_meta[named_feature]  # this is already populated for Data in load_data_ranges above
            for block_meta in ranges:
                # TODO we assume no 'holes' in data here
                interval = get_interval(block_meta)
                if named_feature not in feature_delayed_funcs:
                    feature_delayed_funcs[named_feature] = {}
                feature_delayed = load_if_needed(block_meta)
                feature_delayed_funcs[named_feature][interval] = feature_delayed
            return

        grouped_ranges_by_dep_feature = {}
        for dep_named_feature in fd_type.dep_upstream_schema_named():
            dep_ranges = feature_ranges_meta[dep_named_feature]
            grouped_ranges_by_dep_feature[dep_named_feature] = fd_type.group_dep_ranges(dep_ranges, dep_named_feature)

        overlaps = get_ranges_overlaps(grouped_ranges_by_dep_feature)
        ranges = []
        for interval, overlap in overlaps.items():
            result_meta = calculate_feature_meta(fd_type, overlap,
                                                 interval)  # TODO is this needed? is it for block or range ?
            ranges.append(result_meta)
            if named_feature not in feature_delayed_funcs:
                feature_delayed_funcs[named_feature] = {}

            # TODO use overlap to fetch results of dep delayed funcs
            dep_delayed_funcs = {}
            for dep_named_feature in overlap:
                ds = []
                for dep_block_meta in overlap[dep_named_feature]:
                    dep_interval = get_interval(dep_block_meta)
                    dep_delayed_func = feature_delayed_funcs[dep_named_feature][dep_interval]
                    ds.append(dep_delayed_func)
                dep_delayed_funcs[dep_named_feature] = ds
            feature_delayed = calculate_feature(fd_type, dep_delayed_funcs, interval)
            feature_delayed_funcs[named_feature][interval] = feature_delayed

        feature_ranges_meta[named_feature] = ranges

    postorder(named_root_feature, tree_traversal_callback)
    # list of root feature delayed funcs for all ranges
    return list(feature_delayed_funcs[named_root_feature].values())
