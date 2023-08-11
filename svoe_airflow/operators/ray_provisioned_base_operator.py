from typing import Dict, Tuple, Optional

from airflow.models import BaseOperator

from svoe_airflow.operators.hooks.ray_hook import RayHook
from client.fast_api_client.models import RayClusterConfig


class RayProvisionedBaseOperator(BaseOperator):
    def __init__(self, dag_args: Dict, **kwargs):
        super().__init__(**kwargs)
        cluster_config, cluster_name = self.parse_cluster_args(dag_args)
        self.ray_hook = RayHook(cluster_config=cluster_config, cluster_name=cluster_name)

    def parse_cluster_args(self, dag_args: Dict) -> Tuple[Optional[RayClusterConfig], Optional[str]]:
        raise NotImplementedError # TODO