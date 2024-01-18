from typing import Optional, Dict

from svoe.featurizer_v2.streaming.api.job_graph.job_graph import JobGraph


class JobClient:

    def submit(
        self,
        job_graph: JobGraph,
        job_config: Optional[Dict] = None
    ):
        if job_config is None:
            job_config = {}
