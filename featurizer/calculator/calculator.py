from typing import Dict, List, Tuple, Optional

import ray

from ray.dag import DAGNode
from ray.types import ObjectRef

from featurizer.features.feature_tree.feature_tree import Feature, postorder
from featurizer.blocks.blocks import meta_to_interval, interval_to_meta, get_overlaps, BlockRangeMeta, \
    prune_overlaps, range_meta_to_interval, ranges_to_interval_dict, BlockMeta, overlaps_keys, is_sorted_intervals
from portion import Interval, IntervalDict, closed

from featurizer.calculator.tasks import calculate_feature, load_if_needed, bind_and_cache, context, \
    lookahead_shift_blocks, point_in_time_join_block, load_and_preprocess, gen_synth_events
from common.time.utils import convert_str_to_seconds


# TODO re: cache https://discuss.ray.io/t/best-way-to-share-memory-for-ray-tasks/3759
# https://sourcegraph.com/github.com/ray-project/ray@master/-/blob/python/ray/tests/test_object_assign_owner.py?subtree=true


def build_feature_task_graph(
    dag: Dict[Feature, Dict[Interval, Dict[Interval, DAGNode]]], # DAGNodes per feature per range
    feature: Feature,
    data_ranges_meta: Dict[Feature, List[BlockRangeMeta]],
    obj_ref_cache: Dict[str, Dict[Interval, Tuple[int, Optional[ObjectRef]]]],
    features_to_store: Optional[List[Feature]] = None,
    stored_feature_blocks_meta: Optional[Dict[Feature, Dict[Interval, BlockMeta]]] = None,
) -> Dict[Feature, Dict[Interval, Dict[Interval, DAGNode]]]:
    features_ranges_meta = {}

    def tree_traversal_callback(feature: Feature):
        if feature.feature_definition.is_data_source():
            # leafs
            # TODO decouple derived feature_ranges_meta and input data ranges meta
            ranges = data_ranges_meta[feature]  # this is already populated for Data in load_data_ranges above
            for block_range_meta in ranges:
                if feature not in dag:
                    dag[feature] = {}
                range_interval = range_meta_to_interval(block_range_meta)
                nodes = {}
                for block_meta in block_range_meta:
                    interval = meta_to_interval(block_meta)
                    # node = load_if_needed.bind(path, False)
                    ctx = context(feature.feature_key, interval)
                    if feature.feature_definition.is_synthetic():
                        node = bind_and_cache(gen_synth_events, obj_ref_cache, ctx, interval=interval, synth_data_def=feature.feature_definition, params=feature.params)
                    else:
                        path = block_meta['path']
                        # TODO call load_and_preprocess only if data_def needs preproc, otherwise call load_if_needed
                        # this will save workers
                        # node = bind_and_cache(load_if_needed, obj_ref_cache, ctx, path=path, is_feature=False)
                        node = bind_and_cache(load_and_preprocess, obj_ref_cache, ctx, path=path, data_def=feature.feature_definition, is_feature=False)

                    # TODO validate no overlapping intervals here
                    nodes[interval] = node

                # TODO check if duplicate feature/interval
                dag[feature][range_interval] = nodes
            return

        ranges_per_dep_feature = {}
        for dep_feature in feature.children:
            meta = data_ranges_meta[dep_feature] if dep_feature.feature_definition.is_data_source() else features_ranges_meta[dep_feature]
            ranges_per_dep_feature[dep_feature] = ranges_to_interval_dict(meta)

        range_intervals = prune_overlaps(get_overlaps(ranges_per_dep_feature))
        for range_interval in range_intervals:
            range_meta_per_dep_feature = range_intervals[range_interval]

            grouped_ranges_by_dep_feature = {}
            for dep_feature in feature.children:
                dep_ranges = range_meta_per_dep_feature[dep_feature]
                # TODO this should be in Feature class
                grouped_ranges_by_dep_feature[dep_feature] = feature.feature_definition.group_dep_ranges(dep_ranges, feature, dep_feature)

            overlaps = get_overlaps(grouped_ranges_by_dep_feature)
            block_range_meta = []
            nodes = {}
            for interval, overlap in overlaps.items():
                # TODO add size_kb/memory_size_kb to proper size memory usage for aggregate tasks downstream
                result_meta = interval_to_meta(interval)
                block_range_meta.append(result_meta)
                if feature not in dag:
                    dag[feature] = {}

                # TODO use overlap to fetch results of dep delayed funcs
                dep_nodes = {}
                for dep_feature in overlap:
                    ds = []
                    for dep_block_meta in overlap[dep_feature]:
                        dep_interval = meta_to_interval(dep_block_meta)
                        dep_node = dag[dep_feature][range_interval][dep_interval]
                        ds.append(dep_node)
                    dep_nodes[dep_feature] = ds

                ctx = context(feature.feature_key, interval)
                if stored_feature_blocks_meta is not None and feature in stored_feature_blocks_meta and interval in stored_feature_blocks_meta[feature]:
                    path = stored_feature_blocks_meta[feature][interval]['path']
                    # node = load_if_needed.bind(path, True)
                    node = bind_and_cache(load_if_needed, obj_ref_cache, ctx, path=path, is_feature=True)
                else:
                    store = features_to_store is not None and feature in features_to_store
                    # node = calculate_feature.bind(feature, dep_nodes, interval, store)
                    node = bind_and_cache(calculate_feature, obj_ref_cache, ctx, feature=feature, dep_refs=dep_nodes, interval=interval, store=store)

                # TODO validate interval is within range_interval
                nodes[interval] = node

            # TODO check if range_interval intersects with existing keys/intervals
            dag[feature][range_interval] = nodes
            # TODO check if duplicate feature
            if feature not in features_ranges_meta:
                features_ranges_meta[feature] = [block_range_meta]
            else:
                features_ranges_meta[feature].append(block_range_meta)

    postorder(feature, tree_traversal_callback)

    return dag


def build_feature_set_task_graph(
    features: List[Feature],
    data_ranges_meta: Dict[Feature, List[BlockRangeMeta]],
    obj_ref_cache: Dict[str, Dict[Interval, Tuple[int, Optional[ObjectRef]]]],
    features_to_store: Optional[List[Feature]] = None,
    stored_feature_blocks_meta: Optional[Dict[Feature, Dict[Interval, BlockMeta]]] = None,
) -> Dict[Feature, Dict[Interval, Dict[Interval, DAGNode]]]:
    dag = {}
    for feature in features:
        dag = build_feature_task_graph(
            dag, feature, data_ranges_meta, obj_ref_cache,
            features_to_store=features_to_store,
            stored_feature_blocks_meta=stored_feature_blocks_meta
        )

    return dag


def build_lookahead_graph(feature_graph: Dict[Interval, Dict[Interval, DAGNode]], lookahead: str) -> Dict[Interval, Dict[Interval, DAGNode]]:
    lookahead_s = convert_str_to_seconds(lookahead)
    res = {}
    for range_interval in feature_graph:
        shifted_nodes = {}
        intervals = []
        nodes = []
        for interval in feature_graph[range_interval]:
            intervals.append(interval)
            nodes.append(feature_graph[range_interval][interval])
        if not is_sorted_intervals(intervals):
            raise ValueError('Intervals should be sorted')

        for i in range(len(intervals)):
            interval = intervals[i]
            group = [nodes[i]]
            end = min(interval.upper + lookahead_s, intervals[-1].upper)
            for j in range(i + 1, len(intervals)):
                if intervals[j].upper <= end or (intervals[j].lower <= end <= intervals[j].upper):
                    group.append(nodes[j])
                else:
                    break
            if i < len(intervals) - 1:
                shifted_node = lookahead_shift_blocks.bind(group, interval, lookahead)
                shifted_nodes[interval] = shifted_node
            else:
                # truncate last interval
                if interval.upper - lookahead_s > interval.lower:
                    interval = closed(interval.lower, interval.upper - lookahead_s)
                    shifted_node = lookahead_shift_blocks.bind(group, interval, lookahead)
                    shifted_nodes[interval] = shifted_node
        res[range_interval] = shifted_nodes

    return res


def point_in_time_join_dag(
    dag: Dict[Feature, Dict[Interval, Dict[Interval, DAGNode]]],
    features_to_join: List[Feature],
    label_feature: Optional[Feature],
    result_owner: Optional[ray.actor.ActorHandle] = None
) -> Dict[Interval, Dict[Interval, DAGNode]]:
    # get range overlaps first
    ranges_per_feature = {}
    for feature in features_to_join:
        if feature not in dag:
            raise ValueError(f'Feature {feature} not found in dag')
        ranges_dict = IntervalDict()
        for range_interval in dag[feature]:
            range_and_node_list = []
            range_dict = dag[feature][range_interval]

            # TODO make sure range_list is ts sorted
            for interval in range_dict:
                range_and_node_list.append((interval, range_dict[interval]))
            if overlaps_keys(range_interval, ranges_dict):
                raise ValueError(f'Overlapping intervals: for {range_interval}')
            ranges_dict[range_interval] = range_and_node_list
        ranges_per_feature[feature] = ranges_dict

    overlapped_range_intervals = prune_overlaps(get_overlaps(ranges_per_feature))

    res = {}
    for range_interval in overlapped_range_intervals:
        nodes_per_feature = overlapped_range_intervals[range_interval]

        nodes_per_feature_per_interval = {}
        for feature in nodes_per_feature:
            nodes_per_interval = IntervalDict()
            for interval_node_tuple in nodes_per_feature[feature]:
                interval = interval_node_tuple[0]
                node = interval_node_tuple[1]
                nodes_per_interval[interval] = node
            nodes_per_feature_per_interval[feature] = nodes_per_interval

        overlaps = get_overlaps(nodes_per_feature_per_interval)

        def get_prev_nodes(cur_nodes_per_feature: Dict[Feature, ObjectRef]) -> Dict[Feature, ObjectRef]:
            res = {}
            for feature in cur_nodes_per_feature:
                # TODO here we assume they are ts sorted
                nodes = list(nodes_per_feature_per_interval[feature].values())
                prev_node = None
                cur_node = cur_nodes_per_feature[feature]
                for i in range(len(nodes)):
                    if nodes[i] == cur_node and i > 0:
                        prev_node = nodes[i - 1]

                if prev_node is not None:
                    res[feature] = prev_node

            return res

        joined_nodes = {}
        for interval in overlaps:
            nodes_per_feature = overlaps[interval]
            # we need to know prev values for join
            # in case one value is at the start of current block and another is in the end of prev block
            prev_interval_nodes = get_prev_nodes(nodes_per_feature)
            # TODO set resource spec here
            join_node = point_in_time_join_block.bind(interval, nodes_per_feature, prev_interval_nodes, label_feature, result_owner)
            joined_nodes[interval] = join_node

        res[range_interval] = joined_nodes

    return res


# TODO for feature scaling https://github.com/online-ml/river/blob/main/river/preprocessing/scale.py
def build_feature_label_set_task_graph(
    features: List[Feature],
    label: Optional[Feature],
    label_lookahead: str,
    data_ranges_meta: Dict[Feature, List[BlockRangeMeta]],
    obj_ref_cache: Dict[str, Dict[Interval, Tuple[int, Optional[ObjectRef]]]],
    features_to_store: Optional[List[Feature]] = None,
    stored_feature_blocks_meta: Optional[Dict[Feature, Dict[Interval, BlockMeta]]] = None,
    result_owner: Optional[ray.actor.ActorHandle] = None
) -> Dict[Interval, Dict[Interval, DAGNode]]:
    dag = build_feature_set_task_graph(
        features=features,
        data_ranges_meta=data_ranges_meta,
        obj_ref_cache=obj_ref_cache,
        features_to_store=features_to_store,
        stored_feature_blocks_meta=stored_feature_blocks_meta
    )
    label_feature = None
    if label is not None:
        lookahead_dag = build_lookahead_graph(dag[label], label_lookahead)
        label_feature = Feature.make_label(label)
        dag[label_feature] = lookahead_dag
        features.append(label_feature)
    return point_in_time_join_dag(dag, features, label_feature, result_owner=result_owner)
