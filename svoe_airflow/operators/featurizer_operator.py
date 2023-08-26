from typing import Any, Dict

from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer
from airflow.utils.context import Context
from airflow.models import BaseOperator

from svoe_airflow.operators.require_cluster_mixin import RequireClusterMixin


class FeaturizerOperator(BaseOperator, RequireClusterMixin):

    # re args https://github.com/ajbosco/dag-factory/issues/121
    def __init__(self, args: Dict, **kwargs):
        BaseOperator.__init__(self, **kwargs)
        RequireClusterMixin.__init__(self, args)
        self.args = args
        self.featurizer_config = self.parse_featurizer_args()

    def parse_featurizer_args(self) -> FeaturizerConfig:
        featurizer_config_raw = self.args.get('featurizer_config', None)
        if featurizer_config_raw is None:
            raise ValueError('No featurizer_config is provided')
        return FeaturizerConfig(**featurizer_config_raw)

    def execute(self, context: Context) -> Any:
        ray_head_address = self.get_cluster_address()
        if ray_head_address is None:
            raise ValueError(f'No head address found for cluster: {self.get_cluster_name()}')
        parallelism = self.args.get('parallelism', None)
        if parallelism is None:
            parallelism = 1
        Featurizer.run(config=self.featurizer_config, ray_address=ray_head_address, parallelism=parallelism)

