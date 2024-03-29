import logging
from typing import Dict, List, Optional

from ray.actor import ActorHandle

from svoe.featurizer_v2.streaming.api.function.function import CollectionSourceFunction, LocalFileSourceFunction, \
    SourceFunction, TimedCollectionSourceFunction
from svoe.featurizer_v2.streaming.api.job_graph.job_graph_builder import JobGraphBuilder
from svoe.featurizer_v2.streaming.api.stream.stream_sink import StreamSink
from svoe.featurizer_v2.streaming.api.stream.stream_source import StreamSource
from svoe.featurizer_v2.streaming.runtime.client.job_client import JobClient

# logger = logging.getLogger(__name__)
logger = logging.getLogger("ray")


class StreamingContext:

    def __init__(self, job_config: Optional[Dict] = None):
        self.job_config = job_config
        self._id_generator = 0
        self.stream_sinks: List[StreamSink] = []
        self.job_master: Optional[ActorHandle] = None

    def generate_id(self):
        self._id_generator += 1
        return self._id_generator

    def add_sink(self, stream_sink: StreamSink):
        self.stream_sinks.append(stream_sink)

    def source(self, source_func: SourceFunction) -> StreamSource:
        return StreamSource(self, source_func)

    def from_values(self, *values) -> StreamSource:
        return self.from_collection(values)

    def from_collection(self, values) -> StreamSource:
        assert values, "values shouldn't be None or empty"
        func = CollectionSourceFunction(values)
        return self.source(func)

    def from_timed_collection(self, values, time_period_s) -> StreamSource:
        assert values, "values shouldn't be None or empty"
        func = TimedCollectionSourceFunction(values, time_period_s)
        return self.source(func)

    def read_text_file(self, filename: str) -> StreamSource:
        # line by line
        func = LocalFileSourceFunction(filename)
        return self.source(func)

    def submit(self):
        job_graph = JobGraphBuilder(stream_sinks=self.stream_sinks).build()
        logger.info(f'Built job graph for {job_graph.job_name}')
        logger.info(f'\n {job_graph.gen_digraph()}')
        job_client = JobClient()
        self.job_master = job_client.submit(job_graph=job_graph, job_config=self.job_config)


    def execute(self, job_name: str):
        # TODO support block to job finish
        # job_submit_result = self.submit(job_name)
        # job_submit_result.wait_finish()
        raise NotImplementedError