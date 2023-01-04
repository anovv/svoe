#!/usr/bin/env python3

import ray
import time
from typing import Optional
from cluster_utils import connect
import ray.autoscaler
from ray.data.dataset import DatasetPipeline, Dataset
import ray.workflow
from ray.air.config import ScalingConfig
from ray.air import session
from ray.experimental.state.api import summarize_tasks
from xgboost_ray import RayDMatrix, RayParams, train
from ray.train.xgboost import XGBoostPredictor
from ray.train.xgboost import XGBoostTrainer
from ray.util.dask import ray_dask_get
import dask


@ray.remote(num_cpus=1)
def sample_task(payload: int, task_id: Optional[int] = None) -> int:
    prefix = f'[Task {task_id}]' if task_id is not None else ''
    print(f'{prefix} Task started')
    time.sleep(payload)
    print(f'{prefix} Task finished after {payload}s')
    dask.persist()
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
refs = []
for task_id in range(0, 10):
    refs.append(sample_task.remote(120, task_id))

for ref in refs:
    ray.get(ref)


