from typing import Dict, List, Optional

from fastapi import FastAPI, UploadFile, Response
import uvicorn
import json, typing

from pydantic import BaseModel

from svoe.featurizer.storage.featurizer_storage import FeaturizerStorage
from svoe.platform.ray_cluster.manager.manager import RayClusterManager, RayClusterConfig
from svoe.common.common_utils import base64_decode
from svoe.platform.svoe_airflow.dag_runner import DagRunner


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
featurizer_storage = FeaturizerStorage()
dag_runner = DagRunner()


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
    res, err = featurizer_storage.store_feature_def(
        owner_id=owner_id,
        feature_group=feature_group,
        feature_definition=feature_definition,
        version=version,
        tags=tags,
        files=files
    )
    return Resp(result=res, error=err)


@app.get('/feature_definition/')
def get_feature_definition_files(
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
):
    zipped_bytes, err = featurizer_storage.get_feature_def_files_zipped(
        owner_id=owner_id,
        feature_group=feature_group,
        feature_definition=feature_definition,
        version=version,
    )

    if zipped_bytes is not None:
        zip_filename = f'{owner_id}-{feature_group}-{feature_definition}-{version}.zip'
        return Response(zipped_bytes, media_type="application/x-zip-compressed", headers={
            'Content-Disposition': f'attachment;filename={zip_filename}'
        })
    else:
        return {
            'res': None,
            'err': err,
        }


@app.post('/run_dag/', response_model=Resp, response_class=PrettyJSONResponse)
def run_dag(
    user_id: str,
    dag_conf_encoded: str
):
    user_defined_dag_conf = {}
    try:
        if dag_conf_encoded is not None:
            user_defined_dag_conf = base64_decode(dag_conf_encoded)
    except Exception as e:
        return Resp(result=None, error=f'Unable to decode base64 dag config: {e}')

    try:
        dag_runner.run_dag(user_id=user_id, user_defined_dag_config=user_defined_dag_conf)
        return Resp(result=True, error=None)
    except Exception as e:
        return Resp(result=None, error=str(e))


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=1228, log_level='info')

