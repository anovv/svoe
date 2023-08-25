from typing import Optional

from airflow.hooks.base import BaseHook

from ray_cluster.manager.manager import RayClusterManager, RayClusterConfig


class RayHook(BaseHook):

    def __init__(self, cluster_config: Optional[RayClusterConfig], cluster_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cluster_config = cluster_config
        self.cluster_name = cluster_name
        self.cluster_manager = RayClusterManager()

    def connect_or_create_cluster(self) -> str:
        # check if cluster already exists
        cluster, err = self.cluster_manager.get_ray_cluster(self.cluster_name) # TODO what if internal error?
        wait_until_ray_cluster_ready_timeout = 30
        if self.cluster_config is not None:
            if cluster is None:
                # provision new cluster
                success, error = self.cluster_manager.create_ray_cluster(self.cluster_config)
                if not success:
                    raise ValueError(f'Unable to create cluster {self.cluster_name}: {error}')
                wait_until_ray_cluster_ready_timeout = 60
        else:
            # user provided name only assuming cluster exists, raise
            if cluster is None:
                raise ValueError(f'Unable to find cluster {self.cluster_name}')

        # verify cluster is healthy
        ray_head_address, error = self.cluster_manager.wait_until_ray_cluster_ready(
            self.cluster_name,
            timeout=wait_until_ray_cluster_ready_timeout
        )
        if ray_head_address is None:
            raise ValueError(f'Can not validate cluster {self.cluster_name}: {error}')
        return ray_head_address

    def delete_cluster(self):
        # TODO retries?
        success, err = self.cluster_manager.delete_ray_cluster(name=self.cluster_name)
        if not success:
            raise ValueError(f'Unable to delete cluster {self.cluster_name}: {err}')
