from typing import Dict, Optional


# Encapsulate the runtime information of a streaming task
class RuntimeContext:
    def __init__(self, task_id: int, task_index: int, parallelism: int, job_config: Optional[Dict] = None):
        self.task_id = task_id
        self.task_index = task_index
        self.parallelism = parallelism
        if job_config is None:
            job_config = {}
        self.job_config = job_config
