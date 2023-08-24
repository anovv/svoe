from typing import Dict, Tuple, Optional, Any

from airflow.models import BaseOperator, Variable
from airflow.utils.context import Context

from svoe_airflow.operators.hooks.ray_hook import RayHook
from ray_cluster.manager.manager import RayClusterConfig


class ClusterOperator(BaseOperator):

    template_fields = ('args',)

    def __init__(self, args: Dict, **kwargs):
        super().__init__(**kwargs)
        self.args = args
        cluster_config, cluster_name, self.operation = self.parse_cluster_args(args)
        self.ray_hook = RayHook(cluster_config=cluster_config, cluster_name=cluster_name)

    def parse_cluster_args(self, args: Dict) -> Tuple[Optional[RayClusterConfig], str, str]:
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

        return cluster_config, cluster_name, args['operation']

    def execute(self, context: Context) -> Any:
        head_addr_var_key = self.ray_head_addr_variable_key(self.ray_hook.cluster_name)
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

    @staticmethod
    def ray_head_addr_variable_key(cluster_name: str) -> str:
        return f'ray_head_addr_{cluster_name}'