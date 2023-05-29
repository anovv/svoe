from typing import Dict, List

from fastapi import FastAPI
import uvicorn
import json, typing

from pydantic import BaseModel
from starlette.responses import Response

from ray_cluster.manager.manager import RayClusterManager


class PrettyJSONResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")


app = FastAPI()
ray_cluster_manager = RayClusterManager()


@app.get('/clusters', response_class=PrettyJSONResponse)
def list_clusters():
    clusters = ray_cluster_manager.list_ray_clusters()
    return clusters


@app.get('/cluster/{name}', response_class=PrettyJSONResponse)
def get_cluster(name: str):
    cluster, err = ray_cluster_manager.get_ray_cluster(name)
    return {'result': cluster, 'error': err}


@app.delete('/cluster/{name}', response_class=PrettyJSONResponse)
def delete_cluster(name: str):
    deleted, err = ray_cluster_manager.delete_ray_cluster(name)
    return {'result': deleted, 'error': err}


class RayClusterConfig(BaseModel):
    user_id: str
    cluster_name: str
    is_minikube: bool
    enable_autoscaling: bool
    head_cpu: float
    head_memory: str
    worker_groups: List[RayClusterWorkerGroupConfig]


@app.post('/cluster/', response_class=PrettyJSONResponse)
def create_cluster(config: RayClusterConfig):
    created, err = ray_cluster_manager.create_ray_cluster(config)
    return {'result': created, 'error': err}


@app.get('/cluster_status/{name}', response_class=PrettyJSONResponse)
def get_cluster_status(name: str):
    status, err = ray_cluster_manager.get_ray_cluster_status(name=name)
    return {'result': status, 'error': err}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=1228, log_level='info')


class RayClusterWorkerGroupConfig(BaseModel):
    group_name: str
    replicas: int
    min_replicas: int
    max_replicas: int
    cpu: float
    memory: str
    ray_resources: Dict
