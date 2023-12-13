from svoe.platform.client.base_client import BaseClient
import yaml

from svoe.platform.client.fast_api_client.api.default import run_dag_run_dag_post
from svoe.common.common_utils import base64_encode
from svoe.platform.client.fast_api_client.models import Resp


class DagRunnerClient(BaseClient):

    def __init__(self):
        super(DagRunnerClient, self).__init__()

    def run_dag(self, dag_yaml_path: str) -> bool:
        user_id = '1'
        with open(dag_yaml_path, 'r') as stream:
            dag_conf = yaml.safe_load(stream)
            dag_conf_encoded = base64_encode(dag_conf)

            return bool(self._parse_and_log_error(Resp.from_dict(
                run_dag_run_dag_post.sync(client=self.client, user_id=user_id, dag_conf_encoded=dag_conf_encoded)
            )))


if __name__ == '__main__':
    client = DagRunnerClient()
    client.run_dag(dag_yaml_path='sample_dag.yaml')


