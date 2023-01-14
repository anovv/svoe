from typing import Union, Dict, Callable, Type, List
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data import Data
from featurizer.features.blocks.blocks import Block, BlockRange, BlockMeta, BlockRangeMeta, get_interval, DataParams
import dask.graph_manipulation
from portion import Interval, IntervalDict


def postorder(node: Type[Union[FeatureDefinition, Data]], callback: Callable, name: str):
    if node.is_data():
        callback(node, name)
        return
    named_children = node.dep_upstream_schema_named()
    for dep_fd, dep_name in named_children:
        postorder(dep_fd, callback, dep_name)

    callback(node, name)

def load_data_ranges(
    fd_type: Type[FeatureDefinition],
    data_params: DataParams,
    start_date: str = None,
    end_date: str = None
) -> Dict:
    # TODO call data catalog service
    return {}


# TODO make IntervalDict support generics to indicate value type hints
def get_ranges_overlaps(grouped_ranges: Dict[str, IntervalDict]) -> IntervalDict:
    # TODO add visualization?
    # https://github.com/AlexandreDecan/portion
    # https://stackoverflow.com/questions/40367461/intersection-of-two-lists-of-ranges-in-python
    d = IntervalDict()
    first_feature_name = list(grouped_ranges.keys())[0]
    for interval, ranges in grouped_ranges[first_feature_name].items():
        d[interval] = {first_feature_name: ranges} # named_ranges_dict

    # join ranges_dict for each feature_name with first to find all possible intersecting intervals
    # and their corresponding BlockRange/BlockRangeMeta objects
    for feature_name, ranges_dict in grouped_ranges.items():
        if feature_name == first_feature_name:
            continue

        def concat(named_ranges_dict, ranges):
            res = named_ranges_dict.copy()
            res[feature_name] = ranges
            return res

        combined = d.combine(ranges_dict, how=concat) # outer join
        d = combined[d.domain() & ranges_dict.domain()] # inner join

    return d


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
    fd_type: Type[FeatureDefinition],
    dep_feature_results: Dict[str, BlockRange], # maps dep feature to BlockRange # TODO List[BlockRangeMeta]?
    interval: Interval
) -> Block:
    # TODO use FeatureDefinition.stream()
    return None


# TODO should be FeatureDefinition method
def calculate_feature_meta(
    fd_type: Type[FeatureDefinition],
    dep_feature_results: Dict[str, BlockRangeMeta], # maps dep feature to BlockRange # TODO List[BlockRangeMeta]?
    interval: Interval
) -> BlockMeta:
    return {
        'start_ts': interval.lower,
        'end_ts': interval.upper,
    }


# graph construction
# TODO make 3d visualization with networkx/graphviz
def build_task_graph(
    fd_type: Type[FeatureDefinition],
    feature_ranges: Dict[str, List] # TODO typehint when decide on BlockRangeMeta/BlockMeta
):
    root_feature_name = f'{fd_type.type_str()}-0'
    feature_delayed_funcs = {} # feature delayed functions per range per feature

    # bottom up/postorder traversal
    def tree_traversal_callback(fd_type: Type[Union[FeatureDefinition, Data]], feature_name: str):
        if fd_type.is_data():
            # leaves
            ranges = feature_ranges[feature_name] # this is already populated for Data in load_data_ranges above
            for block_meta in ranges:
                # TODO we assume no 'holes' in data here
                interval = get_interval(block_meta)
                if feature_name not in feature_delayed_funcs:
                    feature_delayed_funcs[feature_name] = {}
                feature_delayed = load_if_needed(block_meta)
                feature_delayed_funcs[feature_name][interval] = feature_delayed
            return

        grouped_ranges_by_dep_feature = {}
        for dep_fd, dep_feature_name in fd_type.dep_upstream_schema_named():
            dep_ranges = feature_ranges[dep_feature_name]
            grouped_ranges_by_dep_feature[dep_feature_name] = fd_type.group_dep_ranges(dep_ranges, dep_feature_name)

        overlaps = get_ranges_overlaps(grouped_ranges_by_dep_feature)
        ranges = []
        for interval, overlap in overlaps.items():
            result_meta = calculate_feature_meta(fd_type, overlap, interval) # TODO is this needed? is it for block or range ?
            ranges.append(result_meta)
            if feature_name not in feature_delayed_funcs:
                feature_delayed_funcs[feature_name] = {}

            # TODO use overlap to fetch results of dep delayed funcs
            dep_delayed_funcs = {}
            for dep_feature_name in overlap:
                ds = []
                for dep_block_meta in overlap[dep_feature_name]:
                    dep_interval = get_interval(dep_block_meta)
                    dep_delayed_func = feature_delayed_funcs[dep_feature_name][dep_interval]
                    ds.append(dep_delayed_func)
                dep_delayed_funcs[dep_feature_name] = ds
            feature_delayed = calculate_feature(fd_type, dep_delayed_funcs, interval)
            feature_delayed_funcs[feature_name][interval] = feature_delayed

        feature_ranges[feature_name] = ranges


    postorder(fd_type, tree_traversal_callback, root_feature_name)
    # list of root feature delayed funcs for all ranges
    return list(feature_delayed_funcs[root_feature_name].values())
