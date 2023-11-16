from typing import Callable, Any, Optional

from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature


class DataSourceEventEmitter:

    # TODO pass config
    @classmethod
    def instance(cls) -> 'DataSourceEventEmitter':
        raise NotImplementedError

    def register_callback(self, feature: Feature, callback: Callable[[Event], Optional[Any]]):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
