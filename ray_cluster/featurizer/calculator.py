from typing import List, Union, Tuple, Dict, Callable
from collections import OrderedDict
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.utils import convert_str_to_seconds
from streamz import Stream
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


def load_data_ranges(
    data_params: DataParams,
    start_date: str = None,
    end_date: str = None
) -> Dict:
    # TODO call data catalog service
    return {}


def get_ranges_overlaps(grouped_ranges: Dict[str, BlockRangeMeta]) -> List[Tuple[Dict[str, BlockRange], float, float]]:

    return []


# feature def aux methods
# some should be moved to FeatureDefinition class
# TODO move to FeatureDefinition class
def is_windowed(fd: FeatureDefinition, dep_feature_name: str):
    return True # TODO


def get_window(fd: FeatureDefinition, dep_feature_name: str) -> str:
    return '1m'

# TODO this should be a partition_ranges strategy in FeatureDefinition class
# def get_prev_feature_delayed_funcs(
#     from_ts: float,
#     features_delayed_by_range: List[Tuple[Dict, float, float]],
#     window: str,
#     dep_feature_name: str
# ) -> List:
#     # TODO use sampling strategy to load only whats needed
#     res = []
#     beg, end = from_ts - convert_str_to_seconds(window), from_ts
#     for features_delayed_funcs, start_ts, end_ts in features_delayed_by_range:
#         if beg <= start_ts <= end:
#             res.append(features_delayed_funcs[dep_feature_name])
#
#     return res

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
    feature_ranges = load_data_ranges(data_params, start_date, end_date)
    feature_delayed_funcs = {} # feature delayed functions per range per feature

    # bottom up/postorder traversal
    def tree_traversal_callback(fd: FeatureDefinition, feature_name: str):
        if isinstance(fd, Data):
            # leaves
            ranges = feature_ranges[feature_name] # this is already populated for Data in load_data_ranges above
            for block_range_meta in ranges:
                for block_meta in block_range_meta:
                    start_ts, end_ts = get_range(block_meta)
                    if feature_name not in feature_delayed_funcs:
                        feature_delayed_funcs[feature_name] = OrderedDict()
                    feature_delayed = load_if_needed(block_meta)
                    feature_delayed_funcs[feature_name][(start_ts, end_ts)] = feature_delayed
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
                feature_delayed_funcs[feature_name] = OrderedDict()

            # TODO use overlap to fetch results of dep delayed funcs
            dep_delayed_funcs = {}
            for dep_feature_name in overlap:
                ds = []
                for dep_block_meta in overlap[dep_feature_name]:
                    dep_start_ts, dep_end_ts = get_range(dep_block_meta)
                    dep_delayed_func = feature_delayed_funcs[dep_feature_name][(dep_start_ts, dep_end_ts)]
                    ds.append(dep_delayed_func)
                dep_delayed_funcs[dep_feature_name] = ds
            feature_delayed = calculate_feature(fd, dep_delayed_funcs, start_ts, end_ts)
            feature_delayed_funcs[feature_name][(start_ts, end_ts)] = feature_delayed

        feature_ranges[feature_name] = ranges

    postorder(fd, tree_traversal_callback, root_feature_name)

    # list of root feature delayed funcs for all ranges
    return list(feature_delayed_funcs[root_feature_name].values())
