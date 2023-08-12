import os
import unittest

import yaml

from common.common_utils import base64_encode
from common.db.mysql_client import DEFAULT_CONFIG
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient


class TestDagsMysqlClient(unittest.TestCase):

    def test_save_and_read(self):
        os.environ['MYSQL_HOST'] = 'localhost'
        os.environ['MYSQL_PASSWORD'] = ''
        client = DagsMysqlClient()
        owner_id = '1'
        dag_name = 'sample_dag'
        dag_config_encoded = 'abc'
        client.save_db_config_encoded(owner_id=owner_id, dag_name=dag_name, dag_config_encoded=dag_config_encoded)
        confs = client.select_all_configs()
        assert len(confs) == 1
        assert confs[0].owner_id == owner_id
        assert confs[0].dag_name == dag_name
        assert confs[0].dag_config_encoded == dag_config_encoded

    def save(self):
        client = DagsMysqlClient()
        owner_id = '1'
        dag_name = 'sample_dag_2' # TODO infer from yaml
        dag_yaml_path = './sample_dag.yaml'
        with open(dag_yaml_path, 'r') as stream:
            dag_conf = yaml.safe_load(stream)
            dag_config_encoded = base64_encode(dag_conf)
            client.save_db_config_encoded(owner_id=owner_id, dag_name=dag_name, dag_config_encoded=dag_config_encoded)


if __name__ == '__main__':
    # unittest.main()
    t = TestDagsMysqlClient()
    # t.test_save_and_read()
    t.save()