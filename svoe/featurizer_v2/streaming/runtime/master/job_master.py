from typing import Optional, Dict

import ray

from svoe.featurizer_v2.streaming.api.job_graph.job_graph import JobGraph
from svoe.featurizer_v2.streaming.runtime.config.streaming_config import StreamingConfig
from svoe.featurizer_v2.streaming.runtime.core.execution_graph.execution_graph import ExecutionGraph
from svoe.featurizer_v2.streaming.runtime.master.context.job_master_runtime_context import JobMasterRuntimeContext
from svoe.featurizer_v2.streaming.runtime.master.resource_manager.resource_manager import ResourceManager
from svoe.featurizer_v2.streaming.runtime.master.scheduler.job_scheduler import JobScheduler


@ray.remote
class JobMaster:

    def __init__(self, job_config: Optional[Dict]):
        streaming_config = StreamingConfig.from_dict(job_config)
        self.master_config = streaming_config.master_config
        self.runtime_context = JobMasterRuntimeContext(streaming_config)
        self.job_scheduler = JobScheduler(self)
        self.resource_manager = ResourceManager()

    def submit_job(self, job_graph: JobGraph) -> bool:
        execution_graph = ExecutionGraph.from_job_graph(job_graph)

        # set resources
        execution_graph.set_resources(self.master_config.resource_config)

        self.runtime_context.execution_graph = execution_graph
        self.runtime_context.job_graph = job_graph
        return self.job_scheduler.schedule_job()

    def destroy(self):
        self.job_scheduler.destroy_job()
