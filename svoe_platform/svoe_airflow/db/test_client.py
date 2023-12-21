import os
import unittest

from platform.svoe_airflow.db.dags_sql_client import DagsSqlClient


class TestDagsMysqlClient(unittest.TestCase):

    def test_save_and_read(self):
        os.environ['MYSQL_HOST'] = 'localhost'
        os.environ['MYSQL_PASSWORD'] = ''
        client = DagsSqlClient()
        owner_id = '1'
        dag_name = 'sample_dag'
        dag_config_encoded = 'abc'
        client.save_db_config_encoded(owner_id=owner_id, dag_name=dag_name, dag_config_encoded=dag_config_encoded)
        confs = client.select_configs(owner_id=owner_id)
        assert len(confs) == 1
        assert confs[0].owner_id == owner_id
        assert confs[0].dag_name == dag_name
        assert confs[0].dag_config_encoded == dag_config_encoded

        error = 'test_error'
        client.report_compilation_error(dag_name=dag_name, error=error)
        err = client.get_compilation_error(dag_name=dag_name)
        assert err == error


if __name__ == '__main__':
    # unittest.main()
    t = TestDagsMysqlClient()
    t.test_save_and_read()