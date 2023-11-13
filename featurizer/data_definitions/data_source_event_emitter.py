from typing import Callable, Any

from featurizer.data_definitions.data_definition import NamedDataEvent


class DataSourceEventEmitter:

    # TODO pass config
    @classmethod
    def instance(cls) -> 'DataSourceEventEmitter':
        raise NotImplementedError

    def register_callback(self, callback: Callable[[NamedDataEvent], Any]):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
