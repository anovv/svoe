from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
import requests


def test_ray_cluster_manager():
    res = requests.get('http://apiserver-svc.apiserver:1228/clusters').json()

    return res['items']


dag = DAG('test_ray_cluster_manager_dag', description='Test Ray Cluster Manager DAG',
          schedule_interval='0 12 * * *',
          start_date=datetime(2017, 3, 20),
          catchup=False)

operator = PythonOperator(task_id='test_ray_cluster_manager', python_callable=test_ray_cluster_manager, dag=dag)

operator