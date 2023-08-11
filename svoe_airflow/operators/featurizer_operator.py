from typing import Any, Dict

from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer
from airflow.utils.context import Context

from svoe_airflow.operators.ray_provisioned_base_operator import RayProvisionedBaseOperator


class FeaturizerOperator(RayProvisionedBaseOperator):

    def __init__(self, dag_args: Dict, **kwargs):
        super().__init__(dag_args=dag_args, **kwargs)
        self.featurizer_config = self.parse_featurizer_args(dag_args)

    def parse_featurizer_args(self, dag_args) -> FeaturizerConfig:
        raise NotImplementedError # TODO

    def execute(self, context: Context) -> Any:
        ray_head_address = self.ray_hook.connect_or_create_cluster()
        Featurizer.run(config=self.featurizer_config, ray_address=ray_head_address)

