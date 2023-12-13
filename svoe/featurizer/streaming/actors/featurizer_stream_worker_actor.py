from threading import Thread
from typing import Dict, Type

import ray

from svoe.featurizer.data_definitions.data_definition import Event
from svoe.featurizer.data_definitions.data_source_definition import DataSourceDefinition
from svoe.featurizer.streaming.event_emitter.data_source_event_emitter import DataSourceEventEmitter
from svoe.featurizer.streaming.feature_stream_graph import FeatureStreamGraph


@ray.remote
class FeaturizerStreamWorkerActor:

    def __init__(
        self,
        feature_stream_graph: FeatureStreamGraph,
        worker_id: str
    ):
        self.worker_id = worker_id
        # TODO add store callbacks
        self.feature_stream_graph = feature_stream_graph

        # we assume one emitter per emitter_type per worker
        self._emitters_by_type: Dict[str, DataSourceEventEmitter] = {}
        self._emitters_threads_by_type: Dict[str, Thread] = {}
        self._init_emitters()

    # if this worker contains data_sources we need to register emitters
    def _init_emitters(self):
        for feature in self.feature_stream_graph.get_ins():
            if not feature.data_definition.is_data_source():
                # TODO in case of partial feature graph, this should also have emitters and callbacks
                continue

            data_source = feature

            data_source_definition: Type[DataSourceDefinition] = data_source.data_definition
            emitter_type: Type[DataSourceEventEmitter] = data_source_definition.event_emitter_type()
            key = str(emitter_type)

            def emitter_callback(event: Event):
                # TODO set async=True?
                self.feature_stream_graph.get_stream(data_source).emit(event, asynchronous=False)

            if key not in self._emitters_by_type:
                emitter = emitter_type.instance()
                emitter.register_callback(data_source, emitter_callback)
                self._emitters_by_type[key] = emitter
            else:
                emitter = self._emitters_by_type[key]
                emitter.register_callback(data_source, emitter_callback)

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