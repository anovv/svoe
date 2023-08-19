from typing import Any, Dict

from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer
from airflow.utils.context import Context

from svoe_airflow.operators.ray_provisioned_base_operator import RayProvisionedBaseOperator


class FeaturizerOperator(RayProvisionedBaseOperator):

    # re args https://github.com/ajbosco/dag-factory/issues/121

    def __init__(self, args: Dict, **kwargs):
        super().__init__(args=args, **kwargs)
        self.featurizer_config = self.parse_featurizer_args()

    def parse_featurizer_args(self) -> FeaturizerConfig:
        featurizer_config_raw = self.args.get('featurizer_config', None)
        if featurizer_config_raw is None:
            raise ValueError('No featurizer_config is provided')
        return FeaturizerConfig(**featurizer_config_raw)

    def execute(self, context: Context) -> Any:
        ray_head_address = self.ray_hook.connect_or_create_cluster()
        Featurizer.run(config=self.featurizer_config, ray_address=ray_head_address)
        if self.cleanup_cluster:
            self.ray_hook.delete_cluster()

