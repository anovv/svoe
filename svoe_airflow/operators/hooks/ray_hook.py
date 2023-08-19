from typing import Optional

from airflow.hooks.base import BaseHook

from ray_cluster.manager.manager import RayClusterManager, RayClusterConfig

RAY_CLUSTER_NAMESPACE = 'ray-system'
RAY_HEAD_SVC_SUFFIX = 'head-svc'
RAY_HEAD_PORT = '10001'


class RayHook(BaseHook):

    def __init__(self, cluster_config: Optional[RayClusterConfig], cluster_name: Optional[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cluster_config = cluster_config
        self.cluster_name = cluster_name
        self.cluster_manager = RayClusterManager()

    def connect_or_create_cluster(self) -> str:
        if self.cluster_name is None and self.cluster_config is None:
            raise ValueError('Should specify either cluster_config or cluster_name')
        if self.cluster_name is not None and self.cluster_config is not None:
            raise ValueError('Should specify either cluster_config or cluster_name')

        if self.cluster_config is not None:
            self.cluster_name = self.cluster_config.cluster_name
            # provision new cluster
            timeout = 120
            success, error = self.cluster_manager.create_ray_cluster(self.cluster_config)
            if not success:
                raise ValueError(f'Unable to create cluster {self.cluster_name}: {error}')
        else:
            timeout = 30

        # verify cluster is healthy
        is_running, error = self.cluster_manager.wait_until_ray_cluster_running(self.cluster_name, timeout=timeout)
        if not is_running:
            raise ValueError(f'Can not validate cluster {self.cluster_name}: {error}')
        ray_head_address = f'{self.cluster_name}-{RAY_HEAD_SVC_SUFFIX}.{RAY_CLUSTER_NAMESPACE}:{RAY_HEAD_PORT}'
        return ray_head_address

    def delete_cluster(self):
        # TODO retries?
        success, err = self.cluster_manager.delete_ray_cluster(name=self.cluster_name)
        if not success:
            raise ValueError(f'Unable to delete cluster {self.cluster_name}')
