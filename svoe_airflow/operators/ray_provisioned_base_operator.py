from typing import Dict, Tuple, Optional

from airflow.models import BaseOperator

from svoe_airflow.operators.hooks.ray_hook import RayHook
from ray_cluster.manager.manager import RayClusterConfig


class RayProvisionedBaseOperator(BaseOperator):

    template_fields = ('args',)

    def __init__(self, args: Dict, **kwargs):
        super().__init__(**kwargs)
        self.args = args
        cluster_config, cluster_name, cleanup_cluster = self.parse_cluster_args()
        self.cleanup_cluster = cleanup_cluster
        self.ray_hook = RayHook(cluster_config=cluster_config, cluster_name=cluster_name)

    def parse_cluster_args(self) -> Tuple[Optional[RayClusterConfig], Optional[str], bool]:
        cluster_config = None
        cluster_config_raw = self.args.get('cluster_config', None)
        if cluster_config_raw is not None:
            cluster_config = RayClusterConfig(**cluster_config_raw)

        # TODO cluster_name should be appended with user_id for isolation per user
        return cluster_config, self.args.get('cluster_name', None), self.args.get('cleanup_cluster', False)