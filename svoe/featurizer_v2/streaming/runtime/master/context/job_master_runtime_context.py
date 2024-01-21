from svoe.featurizer_v2.streaming.runtime.config.streaming_config import StreamingConfig
from svoe.featurizer_v2.streaming.runtime.master.job_lifecycle.job_status import JobStatus


class JobMasterRuntimeContext:

    def __init__(self, streaming_config: StreamingConfig):
        self.streaming_config = streaming_config
        self.job_status = JobStatus.SUBMITTING
        self.job_graph = None
        self.execution_graph = None