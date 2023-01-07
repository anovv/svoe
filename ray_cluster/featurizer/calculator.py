from typing import List, Union, Tuple, Dict, Callable
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.utils import convert_str_to_seconds
from streamz import Stream
from collections import Collection
from streamz.dataframe import DataFrame
import dask
import dask.graph_manipulation
import pandas as pd

Data = FeatureDefinition # indicates this FD is data input # TODO move to FeatureDefinition subclass


def get_leaves(fd: FeatureDefinition) -> List[str]:
    res = []
    root_feature_name = f'{fd.type()}-0'

    def callback(fd, name):
        if isinstance(fd, Data): # TODO define feature tree leaf here
            res.append(name)

    postorder(fd, callback, root_feature_name)
    return res


def postorder(node: FeatureDefinition, callback: Callable, name: str):
    named_children = node.dep_upstream_schema_named()
    if len(named_children) == 0:
        callback(node, name)
        return
    for dep_fd, dep_name in named_children:
        postorder(dep_fd, callback, dep_name)

    callback(node, name)


# catalog methods
BlockMeta = Dict # TODO represents s3 file metadata: name, time range, size, etc.
BlockRangeMeta = List[BlockMeta] # represents metadata of consecutive blocks

# TODO typdef List[BlockRangeMeta]?

Block = pd.DataFrame
BlockRange = List[Block] # represents consecutive blocks

# TODO here we assume data has no 'holes', in real scenario we should use List[BlockRangeMeta]
BlockRangesMetaDict = Dict[str, BlockRangeMeta]

# TODO make abstraction for users to define data params for each input data channel
DataParams = Dict[str, Dict]

TimeRange = Tuple[float, float]


def get_block_ranges_meta(
    data_name: str,
    data_params: DataParams,
    start_date: str = None,
    end_date: str = None
) -> BlockRangeMeta:
    # TODO call data catalog service
    # TODO here we assume data has no 'holes', in real scenario we should use List[BlockRangeMeta]
    return []


def build_block_ranges_meta_dict(
    root_fd: FeatureDefinition,
    data_params: DataParams,
    start_date: str = None,
    end_date: str = None
) -> BlockRangesMetaDict:
    data_leaves = get_leaves(root_fd)
    block_ranges_meta_dict = {}
    for data_name in data_leaves:
        block_ranges_meta_dict[data_name] = get_block_ranges_meta(data_name, data_params, start_date, end_date)

    return block_ranges_meta_dict


def build_data_ranges(block_ranges_meta_dict: BlockRangesMetaDict) -> List[TimeRange]:
    # TODO add visualization here
    # this func takes blocks for each data input and finds overlaps
    # containing data for all input channels

    # TODO this assumes no 'holes' in data
    def find_next(cur: float):
        closest = []
        for _, block_range_meta in block_ranges_meta_dict:
            # TODO this can be optimized
            next = None
            # TODO this assumes no 'holes' in data
            for block_meta in block_range_meta:
                start_ts = get_start_ts(block_meta)
                if start_ts > cur:
                    next = start_ts
                    break
                end_ts = get_end_ts(block_meta)
                if end_ts > cur:
                    next = end_ts
                    break
            if next is None:
                return None
            closest.append(next)
        return min(closest)

    # TODO indicate holes
    return []


def get_data_block_range_meta(
    blocks_meta_dict: BlockRangesMetaDict,
    data_name: str,
    start: float,
    end: float
) -> BlockRangeMeta:
    return []


# feature def aux methods
# some should be moved to FeatureDefinition class
# TODO move to FeatureDefinition class
def is_windowed(fd: FeatureDefinition, dep_feature_name: str):
    return True # TODO


def get_window(fd: FeatureDefinition, dep_feature_name: str) -> str:
    return '1m'

# TODO this should be a partition_ranges strategy in FeatureDefinition class
def get_prev_feature_delayed_funcs(
    from_ts: float,
    features_delayed_by_range: List[Tuple[Dict, float, float]],
    window: str,
    dep_feature_name: str
) -> List:
    # TODO use sampling strategy to load only whats needed
    res = []
    beg, end = from_ts - convert_str_to_seconds(window), from_ts
    for features_delayed_funcs, start_ts, end_ts in features_delayed_by_range:
        if beg <= start_ts <= end:
            res.append(features_delayed_funcs[dep_feature_name])

    return res

#
# def get_fd_sampling_strategy(
#     fd: FeatureDefinition,
# ) -> str:
#     return '1s'


# s3/data lake aux methods
# TODO move to separate class
@dask.delayed
def load_if_needed(
    block_meta: BlockMeta,
) -> Block:
    # TODO if using Ray's Plasma, check shared obj store first, if empty - load from s3
    # TODO figure out how to split BlockRange -> Block and cache if needed
    return None


@dask.delayed
def calculate_feature(
    fd: FeatureDefinition,
    dep_feature_results: Dict[str, BlockRange], # maps dep feature to BlockRange # TODO List[BlockRangeMeta]?
    start_ts: float,
    end_ts: float
) -> Block:
    # TODO use FeatureDefinition.stream()
    return None


# TODO should be FeatureDefinition method
def calculate_feature_meta(
    fd: FeatureDefinition,
    dep_feature_results: Dict[str, BlockRangeMeta], # maps dep feature to BlockRange # TODO List[BlockRangeMeta]?
    start_ts: float,
    end_ts: float
) -> BlockMeta:
    return None


# graph construction
def build_task_graph(
    fd: FeatureDefinition,
    data_params: Dict,
    start_date: str = None,
    end_date: str = None,
):
    root_feature_name = f'{fd.type()}-0'

    feature_ranges = {} # represents result ranges meta by feature
    load_data_ranges(feature_ranges, data_params, start_date, end_date)
    feature_delayed_funcs = {} # represents list of delayed functions for each range, partitioned by feature name

    # bottom up/postorder traversal
    def tree_traversal_callback(fd: FeatureDefinition, feature_name: str):
        if isinstance(fd, Data):
            # leaves
            # block_chunk = get_data_block_range_meta(block_ranges_meta_dict, feature_name, start_ts, end_ts)
            ranges = feature_ranges[feature_name] # this is already populated for Data in load_data_ranges above
            for range in ranges:
                for block_meta in range:
                    start_ts, end_ts = get_start_ts(block_meta), get_end_ts(block_meta)
                    if feature_name not in feature_delayed_funcs:
                        feature_delayed_funcs[feature_name] = []
                    feature_delayed = load_if_needed(block_meta)
                    feature_delayed_funcs[feature_name].append(start_ts, end_ts, feature_delayed)
            return

        grouped_ranges_by_dep_feature = {}
        for dep_fd, dep_feature_name in fd.dep_upstream_schema_named():
            dep_ranges = feature_ranges[dep_feature_name]
            grouped_ranges_by_dep_feature[dep_feature_name] = fd.group_dep_ranges(dep_ranges, dep_feature_name)

        overlaps = get_ranges_overlaps(grouped_ranges_by_dep_feature)
        ranges = []
        for overlap, start_ts, end_ts in overlaps:
            result_meta = calculate_feature_meta(fd, overlap, start_ts, end_ts) # TODO is this needed? is it for block or range ?
            ranges.append(result_meta)
            if feature_name not in feature_delayed_funcs:
                feature_delayed_funcs[feature_name] = []
            feature_delayed = calculate_feature(fd, overlap, start_ts, end_ts)
            feature_delayed_funcs[feature_name].append(start_ts, end_ts, feature_delayed)

        feature_ranges[feature_name] = ranges

    postorder(fd, tree_traversal_callback, root_feature_name)

    # list of root feature delayed funcs for all ranges
    return list(map(lambda f: f[root_feature_name][0][2], feature_delayed_funcs))
