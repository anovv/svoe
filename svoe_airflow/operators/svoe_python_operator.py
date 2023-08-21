from typing import Dict, Any

from svoe_airflow.operators.ray_provisioned_base_operator import RayProvisionedBaseOperator
from airflow.utils.context import Context


class SvoePythonOperator(RayProvisionedBaseOperator):

    # re args https://github.com/ajbosco/dag-factory/issues/121

    def __init__(self, args: Dict, **kwargs):
        super().__init__(args=args, **kwargs)

    def execute(self, context: Context) -> Any:
        # TODO load code from remote and execute
        pass
