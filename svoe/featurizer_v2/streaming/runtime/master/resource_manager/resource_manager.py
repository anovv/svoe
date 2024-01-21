import enum
from typing import Optional

from pydantic import BaseModel


class ResourceKey(enum.StrEnum):
    CPU = 'CPU'
    MEM = 'MEM'
    GPU = 'GPU'


class Resources(BaseModel):
    num_cpus: Optional[float]
    num_gpus: Optional[float]
    memory: Optional[str]

    @classmethod
    def from_dict(cls, resources_dict) -> 'Resources':
        return Resources(
            num_cpus=float(resources_dict.get(ResourceKey.CPU, None)),
            num_gpus=float(resources_dict.get(ResourceKey.GPU, None)),
            memory=resources_dict.get(ResourceKey.MEM, None)
        )


class ResourceManager:

    # should poll Ray cluster and keep resources state in sync
    pass