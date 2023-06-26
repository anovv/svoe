from typing import List, Dict, Tuple

import ray
from intervaltree import Interval
from ray.dag import DAGNode

from featurizer.features.feature_tree.feature_tree import Feature


def execute_graph_nodes(nodes: List[Tuple[Feature, DAGNode]]) -> Dict[Feature, List[Block]]:
    results_refs_per_feature = {}
    executing_refs_per_feature = {}
    max_concurrent_dags = 12 # num_cpus

    def flatten(refs):
        res = []
        for f in refs:
            res.extend(refs[f])
        return res

    def get_feature_by_ref(ref, d):
        for f in d:
            if ref in d[f]:
                return f
        return None

    i = 0
    # TODO merge this with Scheduler in PipelineRunner
    while i < len(nodes):
        _feature = nodes[i][0]
        node = nodes[i][1]
        num_executing_tasks = 0
        for f in executing_refs_per_feature:
            num_executing_tasks += len(executing_refs_per_feature[f])
        if num_executing_tasks < max_concurrent_dags:
            print(f'Scheduled {i + 1}/{len(nodes)} dags')
            if _feature in executing_refs_per_feature:
                executing_refs_per_feature[_feature].append(node.execute())
            else:
                executing_refs_per_feature[_feature] = [node.execute()]
            i += 1

        ready, remaining = ray.wait(flatten(executing_refs_per_feature), num_returns=1, fetch_local=False, timeout=0.001)
        for ref in ready:
            feature = get_feature_by_ref(ref, executing_refs_per_feature)
            if feature in results_refs_per_feature:
                results_refs_per_feature[feature].append(ref)
            else:
                results_refs_per_feature[feature] = [ref]

            executing_refs_per_feature[feature].remove(ref)

    # all scheduled, wait for completion
    while len(flatten(executing_refs_per_feature)) > 0:
        ready, remaining = ray.wait(flatten(executing_refs_per_feature), num_returns=len(flatten(executing_refs_per_feature)), fetch_local=False,
                                    timeout=0.001)
        for ref in ready:
            feature = get_feature_by_ref(ref, executing_refs_per_feature)
            if feature in results_refs_per_feature:
                results_refs_per_feature[feature].append(ref)
            else:
                results_refs_per_feature[feature] = [ref]

            executing_refs_per_feature[feature].remove(ref)

    return {feature: ray.get(results_refs_per_feature[feature]) for feature in results_refs_per_feature}


def flatten_feature_set_task_graph(
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
