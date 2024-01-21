from svoe.featurizer_v2.streaming.runtime.master.job_master import JobMaster


class JobScheduler:

    def __init__(self, job_master: JobMaster):
        self.job_master = job_master

    def schedule_job(self) -> bool:
        pass

    def _prepare_job_submission(self) -> bool:
        pass

    def _do_job_submission(self) -> bool:
        pass

    def _destroy_job(self) -> bool:
        pass
