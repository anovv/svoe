from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def hello_task(**kwargs):
    arg = kwargs['dag_run'].conf.get('arg', 'default')
    return arg

dag = DAG('hello_world', description='Hello World DAG', start_date=datetime(2017, 3, 20), catchup=False)

hello_operator = PythonOperator(task_id='hello_task', python_callable=hello_task, dag=dag)

hello_operator