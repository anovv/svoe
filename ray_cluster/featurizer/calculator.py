from typing import List, Union, Tuple, Dict
from featurizer.features.definitions.feature_definition import FeatureDefinition
from streamz import Stream
from collections import Collection
from streamz.dataframe import DataFrame
import dask
import dask.graph_manipulation
import pandas as pd

# feature tree methods
FeatureTree = str # TODO represent feature dependencies
FeatureTreeNode = str # TODO represents tree node
# FeatureName = str # TODO represents calculatable feature
Data = str # TODO represent data input, should be a FeatureTree leaf

def build_feature_tree(fd: FeatureDefinition) -> FeatureTree:
    return "" # TODO

def get_leaves(feature_tree: FeatureTree) -> List[Data]:
    return []

def traverse_feature_tree(feature_tree: FeatureTree) -> Collection[FeatureTreeNode]:
    return []

def get_feature(node: FeatureTreeNode) -> FeatureDefinition:
    return None # TODO

def get_children(node: FeatureTreeNode) -> List[FeatureTreeNode]:
    return []

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
def is_windowed(fd: FeatureDefinition, dep: FeatureDefinition):
    return True # TODO

def get_window(fd: FeatureDefinition, dep: FeatureDefinition) -> str:
    return '1m'
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
    dep_feature_results: Dict, # maps dep feature to BlockRange
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
    features_delayed_by_range = [] # tuples of feature_delayed_funcs dict, start_ts, end_ts
    feature_tree = build_feature_tree(fd)
    data_leaves = get_leaves(feature_tree)
    blocks_meta_map = {}
    for data in data_leaves:
        blocks_meta_map[data] = get_block_ranges_meta(data, data_params, start_date, end_date)

    data_ranges = build_data_ranges(blocks_meta_map)

    for i in range(0, len(data_ranges)):
        feature_delayed_funcs = {}
        data_range = data_ranges[i]
        start_ts = data_range[0]
        end_ts = data_range[1]
        for feature_tree_node in traverse_feature_tree(feature_tree):
            feature = get_feature(feature_tree_node)
            block_chunk = get_block_chunk(blocks_meta_map, feature, start_ts, end_ts)
            if isinstance(feature, Data):
                # leaves
                # TODO is start/end needed here?
                feature_delayed_funcs[feature] = load_block_if_needed(block_chunk[0])
                continue
            dep_feature_delayed_funcs = {}
            for dep_feature in get_children(feature_tree_node):
                # [feature_delayed_funcs[dep_feature]
                if is_windowed(feature, dep_feature):
                    window = get_window(feature, dep_feature)
                    dep_delayed_funcs = get_prev_feature_delayed_funcs(features_delayed_by_range, window, dep_feature)
                else:
                    dep_delayed_funcs = [feature_delayed_funcs[dep_feature]]
                dep_feature_delayed_funcs[dep_feature] = dep_delayed_funcs
            feature_delayed = calculate_feature(
                feature,
                dep_feature_delayed_funcs,
                start_ts,
                end_ts
            )
            feature_delayed_funcs[feature] = feature_delayed
        features_delayed_by_range.append((feature_delayed_funcs, start_ts, end_ts))

    res = map(lambda f: f[0][feature], features_delayed_by_range) # list of feature delayed funcs for all ranges
    return res
