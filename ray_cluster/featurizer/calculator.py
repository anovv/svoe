from typing import List, Union, Tuple, Dict, Callable
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.utils import convert_str_to_seconds
from streamz import Stream
from collections import Collection
from streamz.dataframe import DataFrame
import dask
import dask.graph_manipulation
import pandas as pd
import functools


# feature tree methods
# class FeatureTreeNode:
#
#     def __init__(self):
#         self.fd = None
#         self.name = None
#         self.children = []

Data = FeatureDefinition
# FeatureTree = FeatureTreeNode # TODO represent feature dependencies
# # FeatureTreeNode = str # TODO represents tree node
# # FeatureName = str # TODO represents calculatable feature
# Data = FeatureTreeNode # TODO represent data input, should be a FeatureTree leaf
#
# def build_feature_tree(fd: FeatureDefinition) -> FeatureTree:
#     root = FeatureTreeNode()
#     root.name = fd.name()
#
#     return root
#
# def get_leaves(feature_tree: FeatureTree) -> List[Data]:
#     return []
#
# def traverse_feature_tree(feature_tree: FeatureTree) -> Collection[FeatureTreeNode]:
#     return []
#
# def get_feature(node: FeatureTreeNode) -> FeatureDefinition:
#     return None # TODO
#
# def get_children(node: FeatureTreeNode) -> List[FeatureTreeNode]:
#     return []


def get_leaves(fd: FeatureDefinition) -> List[Data]:
    return []


def postorder(node: FeatureDefinition, callback: Callable, name: str):
    named_children = node.dep_upstream_schema_named()
    if len(named_children) == 0:
        callback(node, name)
        return
    for dep_fd, dep_name in named_children:
        postorder(dep_fd, callback, dep_name)

    callback(node, name)

# catalog methods
BlockMeta = str # TODO represents s3 file metdata: name, time range, size, etc.
BlockRangeMeta = List[BlockMeta] # represents metadata of consequitive blocks

Block = pd.DataFrame
BlockRange = List[Block]

def get_block_ranges_meta(
    data: Data,
    data_params: dict,
    start_date: str = None,
    end_date: str = None
) -> List[BlockRangeMeta]:
    # TODO call data catalog service
    return []

def build_data_ranges(blocks_meta_map: Dict) -> List[Tuple[float, float]]:
    return []

def get_block_chunk(blocks_meta_map: Dict, fd: FeatureDefinition, start: float, end: float) -> List[BlockMeta]:
    return []

# feature def aux methods
# some should be moved to FeatureDefinition class
# TODO move to FeatureDefinition class
def is_windowed(fd: FeatureDefinition, dep_feature_name: str):
    return True # TODO

def get_window(fd: FeatureDefinition, dep_feature_name: str) -> str:
    return '1m'

def get_prev_feature_delayed_funcs(
    from_ts: float,
    features_delayed_by_range: List[Tuple[Dict, float, float]],
    window: str,
    dep_feature_name: str
) -> List:
    res = []
    beg, end = from_ts - convert_str_to_seconds(window), from_ts
    for features_delayed_funcs, start_ts, end_ts in features_delayed_by_range:
        if start_ts >= beg and start_ts <= end:
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
def load_block_if_needed(
    block_meta: BlockMeta,
) -> Block:
    # TODO if using Ray's Plasma, check shared obj store first, if empty - load from s3
    return None

@dask.delayed
def calculate_feature(
    fd: FeatureDefinition,
    dep_feature_results: Dict[str, Block], # maps dep feature to BlockRange
    start_ts: float,
    end_ts: float
) -> Block:
    # TODO use FeatureDefinition.stream()
    return None, None


# graph construction
def build_task_graph(
    fd: FeatureDefinition,
    data_params: dict,
    start_date: str = None,
    end_date: str = None,
):

    root_feature_name = f'{fd.type()}-0'
    features_delayed_by_range = [] # tuples of feature_delayed_funcs dict, start_ts, end_ts
    # feature_tree = build_feature_tree(fd)
    data_leaves = get_leaves(fd)
    blocks_meta_map = {}
    for data in data_leaves:
        blocks_meta_map[data] = get_block_ranges_meta(data, data_params, start_date, end_date)

    data_ranges = build_data_ranges(blocks_meta_map)

    for i in range(0, len(data_ranges)):
        feature_delayed_funcs = {}
        data_range = data_ranges[i]
        start_ts = data_range[0]
        end_ts = data_range[1]

        # bottom up/postorder traversal

        # for feature_tree_node in traverse_feature_tree(fd):
        def tree_traversal_callback(fd: FeatureDefinition, feature_name: str):
            # feature_name = get_feature_name(fd)
            block_chunk = get_block_chunk(blocks_meta_map, fd, start_ts, end_ts)
            if isinstance(fd, Data):
                # leaves
                # TODO is start/end needed here?
                feature_delayed_funcs[feature_name] = load_block_if_needed(block_chunk[0])
                return
            dep_feature_delayed_funcs = {}
            for dep_fd, dep_feature_name in fd.dep_upstream_schema_named():
                # [feature_delayed_funcs[dep_feature]
                # TODO check we have dep_feature_name key
                if is_windowed(fd, dep_feature_name):
                    window = get_window(fd, dep_feature_name)
                    dep_delayed_funcs = get_prev_feature_delayed_funcs(start_ts, features_delayed_by_range, window, dep_feature_name)
                else:
                    dep_delayed_funcs = [feature_delayed_funcs[dep_feature_name]]
                # TODO check we have no circular deps
                dep_feature_delayed_funcs[dep_feature_name] = dep_delayed_funcs
            feature_delayed = calculate_feature(
                fd,
                dep_feature_delayed_funcs,
                start_ts,
                end_ts
            )
            # TODO check we have no circular deps
            feature_delayed_funcs[feature_name] = feature_delayed

        postorder(fd, tree_traversal_callback, root_feature_name)
        features_delayed_by_range.append((feature_delayed_funcs, start_ts, end_ts))


    res = map(lambda f: f[0][root_feature_name], features_delayed_by_range) # list of feature delayed funcs for all ranges
    return res
