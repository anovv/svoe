from typing import Dict

from pydantic import BaseModel

from svoe.featurizer_v2.streaming.common.config.resource_config import ResourceConfig
from svoe.featurizer_v2.streaming.runtime.config.scheduler_config import SchedulerConfig


class StreamingWorkerConfig(BaseModel):
    pass


class StreamingMasterConfig(BaseModel):
    resource_config: ResourceConfig
    scheduler_config: SchedulerConfig
    job_name: str


class StreamingConfig(BaseModel):
    master_config: StreamingMasterConfig
    worker_config_tempplate: StreamingWorkerConfig

    @classmethod
    def from_dict(cls, config: Dict) -> 'StreamingConfig':
        raise NotImplementedError