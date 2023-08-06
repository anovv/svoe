from typing import Optional

from airflow.models import BaseOperator

from client.ray_cluster_manager.ray_cluster_manager_client import RayClusterConfig
from client.ray_cluster_manager.ray_cluster_manager_client import RayClusterManagerClient

RAY_CLUSTER_NAMESPACE = 'ray-system'
RAY_HEAD_SVC_SUFFIX = 'head-svc'
RAY_HEAD_PORT = '10001'


class RayClusterProvisionedOperator(BaseOperator):

    def __init__(self, cluster_config: Optional[RayClusterConfig], cluster_name: Optional[str], **kwargs):
        super().__init__(**kwargs)
        self.cluster_manager_client = RayClusterManagerClient()
        if cluster_name is None and cluster_config is None:
            raise ValueError('Should specify either cluster_config or cluster_name')
        if cluster_name is not None and cluster_config is not None:
            raise ValueError('Should specify either cluster_config or cluster_name')

        if cluster_config is not None:
            self.cluster_name = cluster_config.cluster_name
            # provision new cluster
            timeout = 60
            success = self.cluster_manager_client.create_ray_cluster(cluster_config)
            if not success:
                raise ValueError(f'Unable to create cluste {self.cluster_name}')
        else:
            timeout = 30
            self.cluster_name = cluster_name

        # verify cluster is healthy
        is_running = self.cluster_manager_client.wait_until_ray_cluster_running(self.cluster_name, timeout=timeout)
        if not is_running:
            raise ValueError(f'Can not connect to existing cluster {cluster_name} after {timeout}s')
        self.ray_head_address = f'{self.cluster_name}-{RAY_HEAD_SVC_SUFFIX}.{RAY_CLUSTER_NAMESPACE}:{RAY_HEAD_PORT}'
