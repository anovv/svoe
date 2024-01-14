import logging
from typing import Dict, List

from svoe.featurizer_v2.streaming.api.function.function import CollectionSourceFunction, LocalFileSourceFunction, \
    SourceFunction
from svoe.featurizer_v2.streaming.api.job_graph.job_graph import JobGraph

logger = logging.getLogger(__name__)


class StreamingContext:

    def __init__(self, job_config: Dict):
        self.job_config = job_config
        self._id_generator = 0
        self.stream_sink: List[StreamSink] = []
        self.job_graph: JobGraph

    def generate_id(self):
        self._id_generator += 1
        return self._id_generator

    def source(self, source_func: SourceFunction):
        """Create an input data stream with a SourceFunction

        Args:
            source_func: the SourceFunction used to create the data stream

        Returns:
            The data stream constructed from the source_func
        """
        return StreamSource.build_source(self, source_func)

    def from_values(self, *values):
        """Creates a data stream from values

        Args:
            values: The elements to create the data stream from.

        Returns:
            The data stream representing the given values
        """
        return self.from_collection(values)

    def from_collection(self, values):
        """Creates a data stream from the given non-empty collection.

        Args:
            values: The collection of elements to create the data stream from.

        Returns:
            The data stream representing the given collection.
        """
        assert values, "values shouldn't be None or empty"
        func = CollectionSourceFunction(values)
        return self.source(func)

    def read_text_file(self, filename: str):
        """Reads the given file line-by-line and creates a data stream that
        contains a string with the contents of each such line."""
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