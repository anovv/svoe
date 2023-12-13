import time
from typing import Any

from svoe.platform.client.base_client import BaseClient
from svoe.platform.client.fast_api_client.api.default import delete_cluster_cluster_name_delete, get_cluster_status_cluster_status_name_get
from svoe.platform.client.fast_api_client.api.default import get_cluster_cluster_name_get, create_cluster_cluster_post, \
    list_clusters_clusters_get
from svoe.platform.client.fast_api_client.models import RayClusterConfig, RayClusterWorkerGroupConfig, \
    RayClusterWorkerGroupConfigRayResources, Resp


class RayClusterManagerClient(BaseClient):

    def __init__(self):
        super(RayClusterManagerClient, self).__init__()

    def create_ray_cluster(self, config: RayClusterConfig) -> bool:
        return bool(self._parse_and_log_error(Resp.from_dict(
            create_cluster_cluster_post.sync(client=self.client, json_body=config)
        )))

    def delete_ray_cluster(self, name: str) -> bool:
        return bool(self._parse_and_log_error(Resp.from_dict(
            delete_cluster_cluster_name_delete.sync(client=self.client, name=name)
        )))

    # TODO pass label_selector
    def list_ray_clusters(self) -> Any:
        return self._parse_and_log_error(Resp.from_dict(
            list_clusters_clusters_get.sync(client=self.client)
        ))

    def get_ray_cluster_status(self, name: str) -> Any:
        return self._parse_and_log_error(Resp.from_dict(
            get_cluster_status_cluster_status_name_get.sync(client=self.client, name=name)
        ))

    def get_ray_cluster(self, name: str) -> Any:
        return self._parse_and_log_error(Resp.from_dict(
            get_cluster_cluster_name_get.sync(client=self.client, name=name)
        ))

    def wait_until_ray_cluster_running(self, name: str, timeout: int = 60, delay_between_attempts: int = 1) -> bool:
        status = None
        while timeout > 0:
            try:
                status = self.get_ray_cluster_status(name)

                # TODO: once we add State to Status, we should check for that as well  <if status and status["state"] == "Running":>
                if status and status["head"] and status["head"]["serviceIP"]:
                    return True
            except:
                print("raycluster {} status not set yet, waiting...".format(name))
                time.sleep(delay_between_attempts)
                timeout -= delay_between_attempts

        # TODO log properly
        print("raycluster {} status is not running yet, current status is {}".format(name, status[
            "state"] if status else "unknown"))

        # TODO this does not take into account pod statuses

        return False


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
            cpu=2,
            memory='10Gi',
            ray_resources=RayClusterWorkerGroupConfigRayResources.from_dict({'worker_size_large': 9999999, 'instance_spot': 9999999})
        )]
    )
    # print(client.delete_ray_cluster('test-ray-cluster'))
    # print(client.get_ray_cluster('test-ray-cluster'))
    # print(client.create_ray_cluster(config))
    print(client.wait_until_ray_cluster_running('test-ray-cluster'))
    # print(client.get_ray_cluster_status('test-ray-cluster'))
    # print(client.list_ray_clusters())
    # print(client.delete_ray_cluster('test-ray-cluster'))