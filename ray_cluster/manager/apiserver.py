from fastapi import FastAPI
import uvicorn
import json, typing
from starlette.responses import Response

from manager import RayClusterManager, RayClusterConfig


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
ray_cluster_manager = RayClusterManager('minikube-1')


@app.get('/clusters', response_class=PrettyJSONResponse)
def list_clusters():
    clusters = ray_cluster_manager.list_ray_clusters()
    return clusters


@app.get('/cluster/{name}', response_class=PrettyJSONResponse)
def get_cluster(name: str):
    cluster = ray_cluster_manager.get_ray_cluster(name)
    return cluster


@app.delete('/cluster/{name}', response_class=PrettyJSONResponse)
def delete_cluster(name: str):
    deleted = ray_cluster_manager.delete_ray_cluster(name)
    return {'result': deleted}


@app.post('/cluster/',  response_class=PrettyJSONResponse)
def create_cluster(config: RayClusterConfig):
    created = ray_cluster_manager.create_ray_cluster(config)
    return {'result': created}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=1228, log_level='info')