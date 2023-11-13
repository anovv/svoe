from typing import List, Callable, Union, Any, Dict

import ray

from featurizer.data_definitions.data_definition import GroupedNamedDataEvent, NamedDataEvent
from featurizer.feature_stream.actors.featurizer_stream_worker_actor import FeaturizerStreamWorkerActor
from featurizer.feature_stream.feature_stream_graph import FeatureStreamGraph
from featurizer.features.feature_tree.feature_tree import Feature


@ray.remote
class FeaturizerStreamManagerActor:

    def __init__(self, features: List[Feature], out_callable: Callable[[Union[GroupedNamedDataEvent, NamedDataEvent]], Any]):
        self.features = features
        self.out_callable = out_callable

    def _distribute_features(self) -> List[Dict[Feature, Callable[[NamedDataEvent], Any]]]:
        # TODO scaling happens here

        group = {}

        return []