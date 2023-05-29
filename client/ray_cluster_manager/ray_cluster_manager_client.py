import logging
from typing import Any

from client.base_client import BaseClient
from client.ray_cluster_manager.fast_api_client import Client
from client.ray_cluster_manager.fast_api_client.api.default import create_cluster_cluster_post, \
    delete_cluster_cluster_name_delete
from client.ray_cluster_manager.fast_api_client.models import RayClusterConfig, RayClusterWorkerGroupConfig, \
    RayClusterWorkerGroupConfigRayResources


log = logging.getLogger(__name__)


class RayClusterManagerClient(BaseClient):

    def __init__(self):
        super(RayClusterManagerClient, self).__init__()
        self.client = Client(
            base_url=self.base_url,
            follow_redirects=True,
            raise_on_unexpected_status=True,
            timeout=120,
            verify_ssl=False
        )

    def create_ray_cluster(self, config: RayClusterConfig) -> bool:
        resp = create_cluster_cluster_post.sync(client=self.client, json_body=config)
        if resp['result']:
            return True
        else:
            log.info(resp['error'])
            return False

    def delete_ray_cluster(self, name: str) -> bool:
        resp = delete_cluster_cluster_name_delete.sync(client=self.client, name=name)
        if resp['result']:
            return True
        else:
            log.info(resp['error'])
            return False

    # TODO pass label_selector
    def list_ray_clusters(self) -> Any:
        # TODO
        return None

    def get_ray_cluster_status(self, name: str) -> Any:
        # TODO
        return None

    def wait_for_cluster_ready(self, name: str, timeout_s: 30) -> Any:
        # TODO
        return None


if __name__ == '__main__':
    client = RayClusterManagerClient()
    config = RayClusterConfig(
        user_id='1',
        cluster_name='test-ray-cluster',
        is_minikube=True,
        enable_autoscaling=False,
        head_cpu=1,
        head_memory='3Gi',
        worker_groups=[RayClusterWorkerGroupConfig(
            group_name='workers',
            replicas=3,
            min_replicas=0,
            max_replicas=3,
            cpu=1,
            memory='3Gi',
            ray_resources=RayClusterWorkerGroupConfigRayResources.from_dict({'worker_size_small': 9999999, 'instance_on_demand': 9999999})
        )]
    )
    # client.create_ray_cluster(config)
    print(client.delete_ray_cluster('test-ray-cluster'))