
from typing import Dict, Any, Collection, Mapping, Callable, Type

from common.common_utils import get_callable_from_remote_code_file
from svoe_airflow.operators.ray_provisioned_base_operator import RayProvisionedBaseOperator
from airflow.utils.context import Context
from utils.s3.s3_utils import download_dir


# https://github.com/anyscale/airflow-provider-ray/blob/main/ray_provider/decorators/ray_decorators.py
class SvoePythonOperator(RayProvisionedBaseOperator):

    # re args https://github.com/ajbosco/dag-factory/issues/121

    def __init__(
        self,
        args: Dict,
        op_args: Collection[Any] | None = None,
        op_kwargs: Mapping[str, Any] | None = None,
        **kwargs
    ):
        super().__init__(args=args, **kwargs)
        self.callable_path = args['_remote_code_remote_path'] # TODO sync with client keys
        self.op_args = op_args or ()
        self.op_kwargs = op_kwargs or {}
        self.python_callable = None

    def execute(self, context: Context) -> Any:
        # TODO call RayHook's methods
        temp_dir, paths = download_dir(self.callable_path)
        python_file_path = paths[0]
        if self.python_callable is None:
            self.python_callable = get_callable_from_remote_code_file(python_file_path)
        temp_dir.cleanup()
        return self.python_callable(*self.op_args, **self.op_kwargs)


if __name__ == '__main__':
    python_file_path = '/Users/anov/svoe_junk/py_files/test_remote_code_v1.py'
    callable = get_callable_from_remote_code_file(python_file_path)
    callable('a')

