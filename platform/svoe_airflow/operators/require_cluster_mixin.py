from typing import Optional, Dict, Tuple
from platform.ray_cluster.manager.manager import RayClusterConfig
from airflow.models import Variable


class RequireClusterMixin:

    def __init__(self, args: Dict):
        self.args = args
        _, self.cluster_name, _ = RequireClusterMixin.parse_cluster_args(self.args)

    def get_cluster_address(self) -> str:
        head_addr_var_key = RequireClusterMixin.ray_head_addr_variable_key(cluster_name=self.cluster_name)
        return Variable.get(head_addr_var_key, None)

    def get_cluster_name(self) -> str:
        return self.cluster_name

    @staticmethod
    def parse_cluster_args(args: Dict) -> Tuple[Optional[RayClusterConfig], str, Optional[str]]:
        cluster_config = None
        cluster_config_raw = args.get('cluster_config', None)
        user_defined_cluster_name = args.get('cluster_name', None)
        if cluster_config_raw is not None:
            cluster_config = RayClusterConfig(**cluster_config_raw)
            user_defined_cluster_name = cluster_config.cluster_name

        if user_defined_cluster_name is None:
            raise ValueError(f'Should provide cluster name either in args or cluster config')

        user_id = args['user_id']
        cluster_name = f'user-{user_id}-{user_defined_cluster_name}'
        # make sure we change user_defined_cluster_name in config to cluster_name
        if cluster_config is not None:
            cluster_config.cluster_name = cluster_name

        return cluster_config, cluster_name, args.get('operation', None)

    @staticmethod
    def ray_head_addr_variable_key(cluster_name: str) -> str:
        return f'ray_head_addr_{cluster_name}'


