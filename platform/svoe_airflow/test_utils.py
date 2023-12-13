import os
import tempfile
import unittest
import yaml

from svoe.common.common_utils import base64_encode
from platform.svoe_airflow.db.models import DagConfigEncoded
from platform.svoe_airflow.utils import construct_dag_yaml_path, store_configs_to_yaml_files, DEFAULT_DAG_YAML_SUFFIX, diff, sync_configs


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

    def test_diff_and_sync(self):
        dag_conf = {
            'a': 1,
            'b': 2
        }
        dag_conf_encoded = base64_encode(dag_conf)
        owner_id = '1'
        dag_name_to_add = 'sample_dag_add'
        dag_name_to_delete = 'sample_dag_delete'
        with tempfile.TemporaryDirectory() as dags_folder:
            expected_file_path_to_add = construct_dag_yaml_path(
                dags_folder=dags_folder,
                dag_name=dag_name_to_add,
                suffix=DEFAULT_DAG_YAML_SUFFIX
            )

            expected_file_path_to_delete = construct_dag_yaml_path(
                dags_folder=dags_folder,
                dag_name=dag_name_to_delete,
                suffix=DEFAULT_DAG_YAML_SUFFIX
            )

            model_to_delete = DagConfigEncoded(owner_id=owner_id, dag_name=dag_name_to_delete, dag_config_encoded=dag_conf_encoded)
            store_configs_to_yaml_files(confs=[model_to_delete], dags_folder=dags_folder, suffix=DEFAULT_DAG_YAML_SUFFIX)


            model_to_add = DagConfigEncoded(owner_id=owner_id, dag_name=dag_name_to_add, dag_config_encoded=dag_conf_encoded)
            mock_db_return = [model_to_add]

            to_add, to_delete = diff(confs=mock_db_return, dags_folder=dags_folder, suffix=DEFAULT_DAG_YAML_SUFFIX)

            assert to_delete == [expected_file_path_to_delete]
            assert to_add == mock_db_return

            sync_configs(confs=mock_db_return, dags_folder=dags_folder, suffix=DEFAULT_DAG_YAML_SUFFIX)
            assert os.path.isfile(expected_file_path_to_add)
            assert not os.path.isfile(expected_file_path_to_delete)


if __name__ == '__main__':
    # unittest.main()
    t = TestSvoeAirflowUtils()
    t.test_parse_and_store_configs()
    t.test_diff_and_sync()