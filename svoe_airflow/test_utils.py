import os
import tempfile
import unittest
import yaml

from common.common_utils import base64_encode
from svoe_airflow.db.models import DagConfigEncoded
from svoe_airflow.utils import construct_dag_yaml_path, store_configs_to_yaml_files, DEFAULT_DAG_YAML_SUFFIX


class TestSvoeAirflowUtils(unittest.TestCase):

    def test_parse_and_store_configs(self):
        dag_conf = {
            'a': 1,
            'b': 2
        }
        owner_id = '1'
        dag_name = 'sample_dag'
        with tempfile.TemporaryDirectory() as dags_folder:
            expected_file_path = construct_dag_yaml_path(
                dags_folder=dags_folder,
                owner_id=owner_id,
                dag_name=dag_name,
                suffix=DEFAULT_DAG_YAML_SUFFIX
            )
            dag_conf_encoded = base64_encode(dag_conf)
            model = DagConfigEncoded(owner_id=owner_id, dag_name=dag_name, dag_config_encoded=dag_conf_encoded)
            store_configs_to_yaml_files(confs=[model], dags_folder=dags_folder, suffix=DEFAULT_DAG_YAML_SUFFIX)
            assert os.path.isfile(expected_file_path)
            with open(expected_file_path) as f:
                res_dag_conf = yaml.safe_load(f)
                assert dag_conf == res_dag_conf


if __name__ == '__main__':
    # unittest.main()
    t = TestSvoeAirflowUtils()
    t.test_parse_and_store_configs()