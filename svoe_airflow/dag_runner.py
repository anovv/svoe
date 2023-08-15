import time
from datetime import datetime, timezone
from typing import Dict

from airflow_client.client import ApiClient, Configuration
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DAGRunApi
from airflow_client.client.model.dag_run import DAGRun

from common.common_utils import base64_encode
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient
from svoe_airflow.utils import user_dag_conf_to_airflow_dag_conf


class DagRunner:

    def __init__(self):
        self.db_client = DagsMysqlClient()

        # TODO pass via env vars/config
        self.airflow_api_client = ApiClient(Configuration(
            host='airflow-webserver.airflow.svc.cluster.local:8080/api/v1',
            username='admin',
            password='admin'
        ))
        self.airflow_dag_api_instance = DAGApi(self.airflow_api_client)
        self.airflow_dag_run_api_instance = DAGRunApi(self.airflow_api_client)

    def run_dag(self, user_id: str, user_defined_dag_config: Dict):
        # delete previous dag instance for this user
        self.db_client.delete_dags_for_user(user_id)

        # construct airflow dag config, encoded it and store in db
        dag_name, dag_config = user_dag_conf_to_airflow_dag_conf(user_defined_dag_config, user_id)
        dag_config_encoded = base64_encode(dag_config)
        self.db_client.save_db_config_encoded(owner_id=user_id, dag_name=dag_name, dag_config_encoded=dag_config_encoded)

        # wait for Airflow to pick up dag_config from db
        timeout = 60
        dag = None
        start = time.time()
        last_exception = None
        while dag is None and (time.time() - start < timeout):
            try:
                dag = self.airflow_dag_api_instance.get_dag(dag_id=dag_name)
            except Exception as e:
                last_exception = e
                time.sleep(1)

        if dag is None:
            raise ValueError(f'Unable to get validate dag in db after {timeout}s, last execption: {last_exception}')

        # run dag
        now = datetime.now().astimezone(tz=timezone.utc)
        now_ts = int(round(now.timestamp()))

        dag_run_id = f'dag-run-{user_id}-{now_ts}'

        # TODO add meta (user_id, env, etc.)
        dag_run = DAGRun(
            dag_run_id=dag_run_id,
            logical_date=now,
            execution_date=now,
            conf={},
        )

        # TODO check if user has existing dags running and set limit?
        # TODO parse api_response?
        api_response = self.airflow_dag_run_api_instance.post_dag_run(dag_id=dag_name, dag_run=dag_run)
