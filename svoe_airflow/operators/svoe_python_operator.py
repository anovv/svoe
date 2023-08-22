import os
import sys
from typing import Dict, Any, Collection, Mapping, Callable

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
        self.callable_path = args['callable_path']
        self.op_args = op_args or ()
        self.op_kwargs = op_kwargs or {}
        self.python_callable = None

    def execute(self, context: Context) -> Any:
        temp_dir, paths = download_dir(self.callable_path)
        python_file_path = paths[0]
        if self.python_callable is None:
            self.python_callable = self._get_callable_from_file(python_file_path)
        temp_dir.cleanup()
        return self.python_callable(*self.op_args, **self.op_kwargs)

    def _get_callable_from_file(self, python_file_path) -> Callable:
        # a/b/c/file.py
        p = python_file_path.split('/')
        to_import = p[len(p) - 1].removesuffix('.py')
        dir = python_file_path.removesuffix(p[len(p) - 1])
        sys.path.append(os.path.abspath(dir))
        class_name = 'SvoeRemoteCode' # TODO parse to_import
        module = __import__(to_import, fromlist=[class_name])
        clazz = getattr(module, class_name)
        # todo cast clazz to RemoteCodeBase and get callable from therre
        return

