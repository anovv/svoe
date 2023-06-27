from typing import List, Dict, Tuple, Any

import ray
from intervaltree import Interval
from ray import ObjectRef
from ray.dag import DAGNode

from featurizer.features.feature_tree.feature_tree import Feature


def execute_graph(dag: Dict[Interval, Dict[Interval, DAGNode]], concurrency: int = 12) -> List[ObjectRef]:
    refs_by_interval = {}

    cur_range_index = 0
    num_ranges = len(dag)
    for range_interval in dag:
        # we create new list of nodes for each range so we can print progress
        # alternatively we can flatten whole graph and execute it
        keyed_nodes = []
        for interval in dag[range_interval]:
            keyed_nodes.append((interval, dag[range_interval][interval]))
        print(f'Executing {cur_range_index + 1}/{num_ranges} range: {range_interval}')
        refs = execute_flattened_nodes(keyed_nodes, concurrency)
        refs_by_interval.update(refs)
        cur_range_index += 1

    # sort resulting refs by interval
    srt = dict(sorted(refs_by_interval.items()))
    res = []
    for ref_list in srt.values():
        res.extend(ref_list)

    return res

# executes
def execute_flattened_nodes(nodes: List[Tuple[Any, DAGNode]], concurrency: int) -> Dict[Any, List[ObjectRef]]:
    results_refs_per_key = {}
    executing_refs_per_key = {}

    def flatten(refs):
        res = []
        for k in refs:
            res.extend(refs[k])
        return res

    def get_key_by_ref(ref, d):
        for k in d:
            if ref in d[k]:
                return k
        return None

    i = 0
    # TODO merge this with Scheduler in PipelineRunner
    while i < len(nodes):
        _key = nodes[i][0]
        node = nodes[i][1]
        num_executing_tasks = 0
        for k in executing_refs_per_key:
            num_executing_tasks += len(executing_refs_per_key[k])
        if num_executing_tasks < concurrency:
            print(f'Scheduled {i + 1}/{len(nodes)} dags')
            if _key in executing_refs_per_key:
                executing_refs_per_key[_key].append(node.execute())
            else:
                executing_refs_per_key[_key] = [node.execute()]
            i += 1

        ready, remaining = ray.wait(flatten(executing_refs_per_key), num_returns=1, fetch_local=False, timeout=0.001)
        for ref in ready:
            key = get_key_by_ref(ref, executing_refs_per_key)
            if key in results_refs_per_key:
                results_refs_per_key[key].append(ref)
            else:
                results_refs_per_key[key] = [ref]

            results_refs_per_key[key].remove(ref)

    # all scheduled, wait for completion
    while len(flatten(executing_refs_per_key)) > 0:
        ready, remaining = ray.wait(flatten(executing_refs_per_key), num_returns=len(flatten(executing_refs_per_key)), fetch_local=False,
                                    timeout=0.001)
        for ref in ready:
            feature = get_key_by_ref(ref, executing_refs_per_key)
            if feature in results_refs_per_key:
                results_refs_per_key[feature].append(ref)
            else:
                results_refs_per_key[feature] = [ref]

            executing_refs_per_key[feature].remove(ref)

    # return {feature: ray.get(results_refs_per_key[feature]) for feature in results_refs_per_key}
    return results_refs_per_key


def flatten_feature_set_task_graph_NOT_USED(
    features: List[Feature],
    dag: Dict[Feature, Dict[Interval, Dict[Interval, DAGNode]]]
) -> List[Tuple[Feature, DAGNode]]:
    flattened_dag = {feature: [] for feature in features}
    for feature in features:
        for range_interval in dag[feature]:
            for interval in dag[feature][range_interval]:
                # TODO verify these are ts sorted
                flattened_dag[feature].append(dag[feature][range_interval][interval])
    # round-robin for even execution
    res = []
    cur_feature_pos = 0
    cur_block_index_per_feature = {feature: 0 for feature in features}

    def _finished():
        for feature in cur_block_index_per_feature:
            if cur_block_index_per_feature[feature] < len(flattened_dag[feature]):
                return False
        return True
    while True:
        if _finished():
            break
        cur_feature = features[cur_feature_pos]
        cur_block_index = cur_block_index_per_feature[cur_feature]
        if cur_block_index == len(flattened_dag[cur_feature]):
            cur_feature_pos = (cur_feature_pos + 1)%(len(features))
            continue
        else:
            res.append((cur_feature, flattened_dag[cur_feature][cur_block_index]))
            cur_block_index_per_feature[cur_feature] = cur_block_index + 1
            cur_feature_pos = (cur_feature_pos + 1) % (len(features))

    return res
