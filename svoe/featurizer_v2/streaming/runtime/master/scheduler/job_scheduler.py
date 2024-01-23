import logging

from svoe.featurizer_v2.streaming.runtime.master.context.job_master_runtime_context import JobMasterRuntimeContext
from svoe.featurizer_v2.streaming.runtime.master.job_lifecycle.job_status import JobStatus
from svoe.featurizer_v2.streaming.runtime.master.worker_lifecycle_controller import WorkerLifecycleController

# logger = logging.getLogger(__name__)
logger = logging.getLogger("ray")

class JobScheduler:

    def __init__(self, runtime_context: JobMasterRuntimeContext):
        self.runtime_context = runtime_context
        self.worker_lifecycle_controller = WorkerLifecycleController()

    def schedule_job(self) -> bool:
        self._prepare_job_submission()
        self._do_job_submission()
        return True

    def _prepare_job_submission(self) -> bool:
        logger.info(f'Preparing job {self.runtime_context.job_graph.job_name}...')
        # create workers
        self.worker_lifecycle_controller.create_workers(self.runtime_context.execution_graph)

        # connect and init workers, update exec graph channels
        self.worker_lifecycle_controller.connect_and_init_workers(self.runtime_context.execution_graph)

        logger.info(f'Prepared job {self.runtime_context.job_graph.job_name}.')
        # TODO init master?

        return True

    def _do_job_submission(self) -> bool:
        logger.info(f'Submitting job {self.runtime_context.job_graph.job_name}...')
        # start workers
        self.worker_lifecycle_controller.start_workers(self.runtime_context.execution_graph)
        self.runtime_context.job_status = JobStatus.RUNNING
        logger.info(f'Submitted job {self.runtime_context.job_graph.job_name}.')
        return True

    def destroy_job(self) -> bool:
        pass
