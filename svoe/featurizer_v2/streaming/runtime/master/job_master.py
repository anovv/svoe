from typing import Optional, Dict

import ray

from svoe.featurizer_v2.streaming.runtime.config.streaming_config import StreamingConfig
from svoe.featurizer_v2.streaming.runtime.master.context.job_master_runtime_context import JobMasterRuntimeContext


@ray.remote
class JobMaster:

    def __init__(self, job_config: Optional[Dict]):
        streaming_config = StreamingConfig.from_dict(job_config)
        self.master_config = streaming_config.master_config
        self.runtime_context = JobMasterRuntimeContext(streaming_config)

    def init(self):
        pass