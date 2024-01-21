from pydantic import BaseModel


class Resources(BaseModel):
    num_cpus: float
    num_gpus: float
    memory: str

class ResourceManager:

    # should poll Ray cluster and keep resources state in sync
    pass