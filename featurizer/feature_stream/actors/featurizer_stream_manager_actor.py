from typing import List, Callable, Union, Any, Dict

import ray

from featurizer.feature_stream.actors.featurizer_stream_worker_actor import FeaturizerStreamWorkerActor
from featurizer.feature_stream.feature_stream_graph import GroupedNamedDataEvent, NamedDataEvent, FeatureStreamGraph
from featurizer.features.feature_tree.feature_tree import Feature


@ray.remote
class FeaturizerStreamManagerActor:

    def __init__(self, features: List[Feature], out_callable: Callable[[Union[GroupedNamedDataEvent, NamedDataEvent]], Any]):
        self.features = features
        self.out_callable = out_callable

    def _distribute_features(self) -> Dict[FeaturizerStreamWorkerActor, FeatureStreamGraph]:
        # TODO scaling happens here
        return {}