import logging
from typing import Dict, List

from svoe.featurizer_v2.streaming.api.function.function import CollectionSourceFunction, LocalFileSourceFunction, \
    SourceFunction
from svoe.featurizer_v2.streaming.api.job_graph.job_graph import JobGraph
from svoe.featurizer_v2.streaming.api.stream.stream_sink import StreamSink
from svoe.featurizer_v2.streaming.api.stream.stream_source import StreamSource

logger = logging.getLogger(__name__)


class StreamingContext:

    def __init__(self, job_config: Dict):
        self.job_config = job_config
        self._id_generator = 0
        self.stream_sinks: List[StreamSink] = []
        self.job_graph: JobGraph

    def generate_id(self):
        self._id_generator += 1
        return self._id_generator

    def add_sink(self, stream_sink: StreamSink):
        self.stream_sinks.append(stream_sink)

    def source(self, source_func: SourceFunction):
        return StreamSource(self, source_func)

    def from_values(self, *values):
        return self.from_collection(values)

    def from_collection(self, values):
        assert values, "values shouldn't be None or empty"
        func = CollectionSourceFunction(values)
        return self.source(func)

    def read_text_file(self, filename: str):
        # line by line
        func = LocalFileSourceFunction(filename)
        return self.source(func)

    def submit(self, job_name: str):
        raise NotImplementedError

    def execute(self, job_name: str):
        """Execute the job. This method will block until job finished.

        Args:
            job_name: name of the job
        """
        # TODO support block to job finish
        # job_submit_result = self.submit(job_name)
        # job_submit_result.wait_finish()
        raise NotImplementedError