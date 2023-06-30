from datetime import datetime

from airflow_client.client import ApiClient, Configuration
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DAGRunApi
from airflow_client.client.api.import_error_api import ImportErrorApi
from airflow_client.client.model.dag_run import DAGRun

import dateutil.parser

airflow_api_client = ApiClient(Configuration(
    host='airflow-webserver.airflow.svc.cluster.local:8080/api/v1',
    username='admin',
    password='admin'
))


def test_run_dag():
    api_instance = DAGRunApi(airflow_api_client)
    now = datetime.now()
    print(type(now))
    d = dateutil.parser.parse('1970-01-01T00:00:00.00Z')
    print(type(d))
    # raise
    now_ts = int(round(now.timestamp()))

    dag_run_id = f'dag-run-{0}-{now_ts}'

    dag_run = DAGRun(
        dag_run_id=dag_run_id,
        logical_date=d,
        execution_date=d,
    )
    api_response = api_instance.post_dag_run('hello_world', dag_run)
    print(api_response)


def test_list_dags():
    api_instance = DAGApi(airflow_api_client)
    limit = 100
    offset = 0
    api_response = api_instance.get_dags(limit=limit, offset=offset, only_active=False)
    print(api_response)


def test_list_dag_runs():
    api_instance = DAGRunApi(airflow_api_client)
    limit = 100
    offset = 0
    api_response = api_instance.get_dag_runs('hello_world', limit=limit, offset=offset)
    print(api_response)


def test_delete_dag(dag_id: str):
    api_instance = DAGApi(airflow_api_client)
    api_response = api_instance.delete_dag(dag_id)
    print(api_response)


def test_get_import_errors():
    api_instance = ImportErrorApi(airflow_api_client)
    limit = 100
    offset = 0
    api_response = api_instance.get_import_errors(limit=limit, offset=offset)
    print(api_response)


# test_delete_dag('hello_world')
test_list_dags()
test_get_import_errors()
# test_list_dag_runs()