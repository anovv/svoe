import logging
from typing import Optional, Dict

from svoe.featurizer_v2.streaming.api.job_graph.job_graph import JobGraph
from svoe.featurizer_v2.streaming.runtime.master.job_master import JobMaster

import ray

logger = logging.getLogger(__name__)


class JobClient:

    def submit(
        self,
        job_graph: JobGraph,
        job_config: Optional[Dict] = None
    ):
        # TODO resources
        master = JobMaster.remote(
            job_config=job_config,
            max_restarts=-1
        )
        logger.info('Started JobMaster')
        submit_res = ray.get(master.submit_job(job_graph))
        logger.info(f'Submitted {job_graph.job_name} with status {submit_res}')



