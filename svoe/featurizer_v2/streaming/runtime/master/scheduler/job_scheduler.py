import logging

from svoe.featurizer_v2.streaming.runtime.master.context.job_master_runtime_context import JobMasterRuntimeContext
from svoe.featurizer_v2.streaming.runtime.master.job_lifecycle.job_status import JobStatus
from svoe.featurizer_v2.streaming.runtime.master.worker_lifecycle_controller import WorkerLifecycleController

logger = logging.getLogger(__name__)


class JobScheduler:

    def __init__(self, runtime_context: JobMasterRuntimeContext):
        self.runtime_context = runtime_context
        self.worker_lifecycle_controller = WorkerLifecycleController()

    def schedule_job(self) -> bool:
        pass

    def _prepare_job_submission(self) -> bool:
        # create workers
        dummy_workers_info = self.worker_lifecycle_controller.create_dummy_workers(
            self.runtime_context.execution_graph
        )

        # init workers and update exec graph channels
        self.worker_lifecycle_controller.init_workers_and_update_graph_channels(
            dummy_workers_info,
            self.runtime_context.execution_graph
        )

        # TODO init master?

        return True

    def _do_job_submission(self) -> bool:
        # start workers
        self.worker_lifecycle_controller.start_workers(self.runtime_context.execution_graph)
        self.runtime_context.job_status = JobStatus.RUNNING
        return True

    def destroy_job(self) -> bool:
        pass
