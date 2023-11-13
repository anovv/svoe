from typing import List, Callable, Union, Any, Dict

import ray
import ray.actor

from featurizer.data_definitions.data_definition import GroupedNamedDataEvent, NamedDataEvent
from featurizer.feature_stream.actors.featurizer_stream_worker_actor import FeaturizerStreamWorkerActor
from featurizer.feature_stream.feature_stream_graph import FeatureStreamGraph, FeatureStreamGroupGraph
from featurizer.features.feature_tree.feature_tree import Feature

class FeatureStreamWorkerGraphNode:

    def __init__(self, feature_stream_graph: FeatureStreamGraph, worker: ray.actor.ActorHandle):
        self.feature_stream_graph = feature_stream_graph
        self.worker = worker

    def __hash__(self):
        return hash(self.feature_stream_graph)

    def __eq__(self, other):
        return hash(self) == hash(other)

@ray.remote
class FeaturizerStreamManagerActor:

    def __init__(self, features: List[Feature]):
        self.features = features
        self.feature_stream_group_graph = self._distribute_features()

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

    def build_worker_actor_graph(self) -> Dict[FeatureStreamWorkerGraphNode, List[FeatureStreamWorkerGraphNode]]:
        pass # TODO







