from typing import List, Dict, Optional

import ray.actor

from featurizer.streaming.actors.featurizer_stream_worker_actor import FeaturizerStreamWorkerActor
from featurizer.streaming.feature_stream_graph import FeatureStreamGraph, FeatureStreamGroupGraph
from featurizer.features.feature_tree.feature_tree import Feature


class FeatureStreamWorkerGraphNode:

    @classmethod
    def worker_id(cls, feature_stream_graph: FeatureStreamGraph):
        return f'{FeaturizerStreamWorkerActor.__class__.__name__}_{str(hash(feature_stream_graph))}'

    def __init__(self, feature_stream_graph: FeatureStreamGraph, worker: ray.actor.ActorHandle, worker_id: str):
        self.feature_stream_graph = feature_stream_graph
        self.worker = worker
        self.worker_id = worker_id
        self.upstreams: List[FeatureStreamWorkerGraphNode] = []
        self.downstreams: List[FeatureStreamWorkerGraphNode] = []

    def add_upstream(self, node: 'FeatureStreamWorkerGraphNode'):
        _has = False
        for _node in self.upstreams:
            if _node.worker_id == node.worker_id:
                _has = True
                break
        if not _has:
            self.upstreams.append(node)

    def add_downstream(self, node: 'FeatureStreamWorkerGraphNode'):
        _has = False
        for _node in self.downstreams:
            if _node.worker_id == node.worker_id:
                _has = True
                break
        if not _has:
            self.downstreams.append(node)

    def get_upstreams(self) -> List['FeatureStreamWorkerGraphNode']:
        return self.upstreams

    def get_downstreams(self) -> List['FeatureStreamWorkerGraphNode']:
        return self.downstreams


class FeatureStreamWorkerGraph:

    def __init__(self):
        self.nodes: Dict[str, FeatureStreamWorkerGraphNode] = {}

    def add_node(self, worker_id: str, node: FeatureStreamWorkerGraphNode):
        if worker_id in self.nodes:
            raise RuntimeError('Duplicate worker_id')
        self.nodes[worker_id] = node

    def has_node(self, worker_id: str) -> bool:
        return worker_id in self.nodes

    def get_nodes(self) -> Dict[str, FeatureStreamWorkerGraphNode]:
        return self.nodes

    @classmethod
    def build_from_group_graph(cls, fs_group_graph: FeatureStreamGroupGraph) -> 'FeatureStreamWorkerGraph':
        worker_graph = FeatureStreamWorkerGraph()
        for fsg in fs_group_graph:
            cls._build_graph_dfs(None, fsg, fs_group_graph, worker_graph)

        return worker_graph

    @classmethod
    def _build_graph_dfs(
        cls,
        upstream_node: Optional[FeatureStreamWorkerGraphNode],
        fsg: FeatureStreamGraph,
        fs_group_graph: FeatureStreamGroupGraph,
        worker_graph: 'FeatureStreamWorkerGraph'
    ):
        worker_id = FeatureStreamWorkerGraphNode.worker_id(fsg)
        if worker_graph.has_node(worker_id):
            return

        worker = FeaturizerStreamWorkerActor.remote(fsg, worker_id)
        worker_node = FeatureStreamWorkerGraphNode(fsg, worker, worker_id)
        if upstream_node is not None:
            upstream_node.add_downstream(worker_node)
            worker_node.add_upstream(upstream_node)
        worker_graph.add_node(worker_id, worker_node)

        for dep_fsg in fs_group_graph[fsg]:
            cls._build_graph_dfs(
                worker_node,
                dep_fsg,
                fs_group_graph,
                worker_graph
            )


@ray.remote
class FeaturizerStreamManagerActor:

    def __init__(self, features: List[Feature]):
        self.features = features
        self.feature_stream_group_graph = self._distribute_features()
        self.worker_graph = FeatureStreamWorkerGraph.build_from_group_graph(self.feature_stream_group_graph)

    # TODO make this udf with default implementations
    def _distribute_features(self) -> FeatureStreamGroupGraph:
        # TODO scaling happens here

        # no scaling - one actor
        fsg = FeatureStreamGraph(
            features_or_config=self.features,
            combine_outputs=True,
            combined_out_callback=(lambda e: print(e))
        )
        return {fsg: []}

    def _connect_workers(self, upstream: FeatureStreamWorkerGraphNode, node: FeatureStreamWorkerGraphNode):
        # TODO
        pass

    def _connect_workers_graph(self):
        worker_nodes = self.worker_graph.get_nodes()
        for worker_id in worker_nodes:
            worker_node = worker_nodes[worker_id]
            for upstream_worker_node in worker_node.get_upstreams():
                self._connect_workers(upstream_worker_node, worker_node)

    def run(self):
        worker_nodes = self.worker_graph.get_nodes()
        for worker_id in worker_nodes:
            worker_node = worker_nodes[worker_id]
            worker = worker_node.worker
            worker.start.remote()









