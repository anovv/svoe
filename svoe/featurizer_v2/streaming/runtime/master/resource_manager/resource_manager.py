from typing import Optional

from pydantic import BaseModel


RESOURCE_KEY_CPU = 'CPU'
RESOURCE_KEY_MEM = 'MEM'
RESOURCE_KEY_GPU = 'GPU'


class Resources(BaseModel):
    num_cpus: Optional[float]
    num_gpus: Optional[float]
    memory: Optional[str]

    @classmethod
    def from_dict(cls, resources_dict) -> 'Resources':
        return Resources(
            num_cpus=float(resources_dict.get(RESOURCE_KEY_CPU, None)),
            num_gpus=float(resources_dict.get(RESOURCE_KEY_GPU, None)),
            memory=resources_dict.get(RESOURCE_KEY_MEM, None)
        )


class ResourceManager:

    # should poll Ray cluster and keep resources state in sync
    pass