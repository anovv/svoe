from threading import Thread
from typing import Dict

import ray

from featurizer.data_definitions.data_source_definition import DataSourceDefinition
from featurizer.data_definitions.data_source_event_emitter import DataSourceEventEmitter
from featurizer.features.feature_tree.feature_tree import Feature

@ray.remote
class FeaturizerStreamWorkerActor:

    def __init__(self, feature: Feature):
        self.feature = feature
        self._emitters: Dict[str, DataSourceEventEmitter] = {}
        self._emitters_threads: Dict[str, Thread] = {}

        # TODO what if its is a partial feature?
        # init emitters and emitter threads
        for data_source in feature.get_data_sources():
            if not isinstance(data_source.data_definition, DataSourceDefinition):
                raise RuntimeError('data_source should have DataSourceDefinition')
            data_source_definition: DataSourceDefinition = data_source.data_definition
            emitter = data_source_definition.event_emitter(data_source.params)
            self._emitters[data_source.key] = emitter

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