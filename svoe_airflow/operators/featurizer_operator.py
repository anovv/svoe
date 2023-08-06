from typing import Optional, Any

from client.fast_api_client.models import RayClusterConfig
from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer
from svoe_airflow.operators.ray_cluster_provisioned_operator import RayClusterProvisionedOperator
from airflow.utils.context import Context


class FeaturizerOperator(RayClusterProvisionedOperator):

    def __init__(self, featurizer_config: FeaturizerConfig, cluster_config: Optional[RayClusterConfig], cluster_name: Optional[str], **kwargs):
        super().__init__(cluster_config=cluster_config, cluster_name=cluster_name, **kwargs)
        self.featurizer_config = featurizer_config

    def execute(self, context: Context) -> Any:
        Featurizer.run(config=self.featurizer_config, ray_address=self.ray_head_address)

