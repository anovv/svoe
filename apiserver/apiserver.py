from typing import Dict, List, Optional

from fastapi import FastAPI, UploadFile
import uvicorn
import json, typing

from pydantic import BaseModel
from starlette.responses import Response

import featurizer.api.api
from ray_cluster.manager.manager import RayClusterManager


class RayClusterWorkerGroupConfig(BaseModel):
    group_name: str
    replicas: int
    min_replicas: int
    max_replicas: int
    cpu: float
    memory: str
    ray_resources: Dict


class RayClusterConfig(BaseModel):
    user_id: str
    cluster_name: str
    is_minikube: bool
    enable_autoscaling: bool
    head_cpu: float
    head_memory: str
    worker_groups: List[RayClusterWorkerGroupConfig]


class Resp(BaseModel):
    result: typing.Any
    error: typing.Optional[str]


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
featurizer_api = featurizer.api.api.Api()


@app.get('/clusters', response_model=Resp, response_class=PrettyJSONResponse)
def list_clusters():
    clusters, err = ray_cluster_manager.list_ray_clusters()
    return Resp(result=clusters, error=err)


@app.get('/cluster/{name}', response_model=Resp, response_class=PrettyJSONResponse)
def get_cluster(name: str):
    cluster, err = ray_cluster_manager.get_ray_cluster(name)
    return Resp(result=cluster, error=err)


@app.delete('/cluster/{name}', response_model=Resp, response_class=PrettyJSONResponse)
def delete_cluster(name: str):
    deleted, err = ray_cluster_manager.delete_ray_cluster(name)
    return Resp(result=deleted, error=err)


@app.post('/cluster/', response_model=Resp, response_class=PrettyJSONResponse)
def create_cluster(config: RayClusterConfig):
    created, err = ray_cluster_manager.create_ray_cluster(config)
    return Resp(result=created, error=err)


@app.get('/cluster_status/{name}', response_model=Resp, response_class=PrettyJSONResponse)
def get_cluster_status(name: str):
    status, err = ray_cluster_manager.get_ray_cluster_status(name=name)
    return Resp(result=status, error=err)


# TODO pass param indicating if we want to override existing feature_def
@app.post('/feature_definition/', response_model=Resp, response_class=PrettyJSONResponse)
def upload_feature_definition(
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
    tags: Optional[List[Dict]],
    files: List[UploadFile]
):
    if tags is not None and len(tags) == 0:
        tags = None
    res, err = featurizer_api.store_feature_def(
        owner_id=owner_id,
        feature_group=feature_group,
        feature_definition=feature_definition,
        version=version,
        tags=tags,
        files=files
    )
    return Resp(result=res, error=err)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=1228, log_level='info')

