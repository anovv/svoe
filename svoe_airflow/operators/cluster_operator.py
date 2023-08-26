from typing import Dict, Tuple, Optional, Any

from airflow.models import BaseOperator, Variable
from airflow.utils.context import Context

from svoe_airflow.operators.hooks.ray_hook import RayHook
from svoe_airflow.operators.require_cluster_mixin import RequireClusterMixin


class ClusterOperator(BaseOperator):

    template_fields = ('args',)

    def __init__(self, args: Dict, **kwargs):
        super().__init__(**kwargs)
        self.args = args
        cluster_config, cluster_name, self.operation = RequireClusterMixin.parse_cluster_args(args)
        if self.operation is None:
            raise ValueError('Should provide cluster operation')
        self.ray_hook = RayHook(cluster_config=cluster_config, cluster_name=cluster_name)

    def execute(self, context: Context) -> Any:
        head_addr_var_key = RequireClusterMixin.ray_head_addr_variable_key(self.ray_hook.cluster_name)
        if self.operation == 'create':
            head_addr = self.ray_hook.connect_or_create_cluster()
            Variable.set(key=head_addr_var_key, value=head_addr)
            print(f'Created cluster {self.ray_hook.cluster_name}')
        elif self.operation == 'delete':
            self.ray_hook.delete_cluster()
            Variable.delete(head_addr_var_key)
            print(f'Deleted cluster {self.ray_hook.cluster_name}')
        else:
            raise ValueError('Unsupported cluster operation')
