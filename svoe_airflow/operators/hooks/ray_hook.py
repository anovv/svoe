from typing import Optional

from airflow.hooks.base import BaseHook

from client.fast_api_client.models import RayClusterConfig
from client.ray_cluster_manager.ray_cluster_manager_client import RayClusterManagerClient

RAY_CLUSTER_NAMESPACE = 'ray-system'
RAY_HEAD_SVC_SUFFIX = 'head-svc'
RAY_HEAD_PORT = '10001'


class RayHook(BaseHook):

    def __init__(self, cluster_config: Optional[RayClusterConfig], cluster_name: Optional[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cluster_config = cluster_config
        self.cluster_name = cluster_name
        # TODO we can use RayClusterManager directly here
        self.cluster_manager_client = RayClusterManagerClient()

    def connect_or_create_cluster(self) -> str:
        if self.cluster_name is None and self.cluster_config is None:
            raise ValueError('Should specify either cluster_config or cluster_name')
        if self.cluster_name is not None and self.cluster_config is not None:
            raise ValueError('Should specify either cluster_config or cluster_name')

        if self.cluster_config is not None:
            self.cluster_name = self.cluster_config.cluster_name
            # provision new cluster
            timeout = 60
            success = self.cluster_manager_client.create_ray_cluster(self.cluster_config)
            if not success:
                raise ValueError(f'Unable to create cluste {self.cluster_name}')
        else:
            timeout = 30

        # verify cluster is healthy
        is_running = self.cluster_manager_client.wait_until_ray_cluster_running(self.cluster_name, timeout=timeout)
        if not is_running:
            raise ValueError(f'Can not connect to existing cluster {self.cluster_name} after {timeout}s')
        ray_head_address = f'{self.cluster_name}-{RAY_HEAD_SVC_SUFFIX}.{RAY_CLUSTER_NAMESPACE}:{RAY_HEAD_PORT}'
        return ray_head_address

    def delete_cluster(self):
        # TODO retries?
        success = self.cluster_manager_client.delete_ray_cluster(name=self.cluster_name)
        if not success:
            raise ValueError(f'Unable to delete cluster {self.cluster_name}')
