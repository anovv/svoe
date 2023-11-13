from threading import Thread
from typing import Dict, Type, List, Callable, Any

import ray

from featurizer.data_definitions.data_definition import NamedDataEvent
from featurizer.data_definitions.data_source_definition import DataSourceDefinition
from featurizer.data_definitions.data_source_event_emitter import DataSourceEventEmitter
from featurizer.features.feature_tree.feature_tree import Feature

@ray.remote
class FeaturizerStreamWorkerActor:

    def __init__(self, features_and_callbacks: Dict[Feature, Callable[[NamedDataEvent], Any]]):
        self.features_and_callbacks = features_and_callbacks

        # we assume one emitter per emitter type per worker
        self._emitters_by_type: Dict[str, DataSourceEventEmitter] = {}
        self._emitters_threads_by_type: Dict[str, Thread] = {}
        self._init_emitters()

    # if this worker contains data_sources we need to register emitters
    def _init_emitters_if_needed(self):
        for feature in self.features_and_callbacks:
            if not feature.data_definition.is_data_source():
                continue

            data_source = feature

            data_source_definition: Type[DataSourceDefinition] = data_source.data_definition
            emitter_type: Type[DataSourceEventEmitter] = data_source_definition.event_emitter_type()
            key = str(emitter_type)

            if key not in self._emitters_by_type:
                emitter = emitter_type.instance()
                emitter.register_callback(self.features_and_callbacks[data_source])
                self._emitters_by_type[key] = emitter
            else:
                emitter = self._emitters_by_type[key]
                emitter.register_callback(self.features_and_callbacks[data_source])

            def _start_emitter(_emitter: DataSourceEventEmitter):
                _emitter.start()

            self._emitters_threads[data_source.key] = Thread(target=_start_emitter, args=(emitter,), daemon=True)

    def start(self):
        for _, emitter_thread in self._emitters_threads:
            emitter_thread.start()

    def stop(self):
        for _, emitter in self._emitters:
            emitter.stop()
        # join threads
        for _, emitter_thread in self._emitters_threads:
            emitter_thread.join()