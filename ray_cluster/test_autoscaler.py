import ray
import time
from typing import Optional
from cluster_utils import connect


@ray.remote(num_cpus=1)
def sample_task(payload: int, task_id: Optional[int] = None) -> int:
    prefix = f'[Task {task_id}]' if task_id is not None else ''
    print(f'{prefix} Task started')
    time.sleep(payload)
    print(f'{prefix} Task finished after {payload}s')
    return 1


class SampleActor:
    def __init__(self, actor_id: Optional[int] = None):
        self.actor_id = actor_id
        prefix = f'[Task {actor_id}]' if actor_id is not None else ''
        print(f'{prefix} Actor inited')

    def do_work(self):
        prefix = f'[Task {self.actor_id}]' if self.actor_id is not None else ''
        print(f'{prefix} Actor started doing work...')
        time.sleep(5)
        print(f'{prefix} Actor finished doing work')


connect()
for task_id in range(0, 10):
    sample_task.remote(120)
