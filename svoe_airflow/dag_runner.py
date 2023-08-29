import codecs
import secrets
from pathlib import Path

import time
from datetime import datetime
from typing import Dict, Optional, Generator, Tuple

import yaml
from airflow import DAG
from airflow_client.client import ApiClient, Configuration
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DAGRunApi
from airflow_client.client.api.task_instance_api import TaskInstanceApi
from airflow_client.client.model.dag_run import DAGRun
from dagfactory import DagFactory

from common.s3.s3_utils import upload_dir, delete_by_prefix
from common.common_utils import base64_encode
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient
from svoe_airflow.utils import user_dag_conf_to_airflow_dag_conf

import dagfactory

# AIRFLOW_HOST = 'airflow-webserver.airflow.svc.cluster.local:8080/api/v1'
AIRFLOW_HOST = 'http://localhost:8080/api/v1'
DAG_RUN_ID_PREFIX = 'dag-run'

class DagRunner:

    def __init__(self):
        self.db_client = DagsMysqlClient()

        # TODO pass via env vars/config
        self.airflow_api_client = ApiClient(Configuration(
            host=AIRFLOW_HOST,
            username='admin',
            password='GGWM68cT7gRZXvNP'
        ))
        self.airflow_dag_api = DAGApi(self.airflow_api_client)
        self.airflow_dag_run_api = DAGRunApi(self.airflow_api_client)
        self.airflow_task_instance_api = TaskInstanceApi(self.airflow_api_client)

    def _delete_dag_config_and_metadata(self, user_id: str, dag_name: str):
        # TODO stop associated dag run
        # delete dag metadata from Airflow
        try:
            self.airflow_dag_api.delete_dag(dag_id=dag_name)
            print('deleted meta')
        except:
            # can happen if DAG is not synced to webserver yet
            pass
        # delete config from db
        self.db_client.delete_configs(user_id)
        print('deleted db')

    def run_dag_locally(self, user_defined_dag_config: Dict):
        dag_name, dag_config = user_dag_conf_to_airflow_dag_conf(user_defined_dag_config)
        dag_factory = DagFactory(config=dag_config)
        dags = dag_factory.build_dags()
        dag = list(dags.values())[0]
        dag.test()


    def run_dag(self, user_id: str, user_defined_dag_config: Dict) -> Tuple[str, str]:
        # get prev configs for this user
        confs = self.db_client.select_configs(owner_id=user_id)
        if len(confs) > 1:
            raise RuntimeError(f'User {user_id} has more than 1 conf stored ({len(confs)})')

        # delete previous dag_config in db
        if len(confs) != 0:
            prev_dag_name = confs[0].dag_name
            self._delete_dag_config_and_metadata(user_id=user_id, dag_name=prev_dag_name)

        # construct airflow dag config, encoded it and store in db
        dag_name, dag_config = user_dag_conf_to_airflow_dag_conf(user_defined_dag_config, user_id)
        dag_config_encoded = base64_encode(dag_config)
        self.db_client.save_db_config_encoded(owner_id=user_id, dag_name=dag_name, dag_config_encoded=dag_config_encoded)

        # wait for Airflow to pick up dag_config from db
        timeout = 30
        dag = None
        start = time.time()
        last_exception = None
        while dag is None and (time.time() - start < timeout):
            try:
                dag = self.airflow_dag_api.get_dag(dag_id=dag_name)
            except Exception as e:
                print('Dag is none')
                # check if there were compilation errors
                compilation_error = self.db_client.get_compilation_error(dag_name=dag_name)
                if compilation_error is not None:
                    self._delete_dag_config_and_metadata(user_id=user_id, dag_name=dag_name)
                    # user defined dag is not compilable, report it back
                    raise ValueError(f'Malformed dag, remote trace: {compilation_error}') from None
                else:
                    print('Error is none')
                    last_exception = e
            time.sleep(1)

        if dag is None:
            raise ValueError(f'Unable to get validated dag in db after {timeout}s, last exception: {last_exception}')

        print('dag registered')

        # run dag
        # now = datetime.now().astimezone(tz=timezone.utc) # TODO check timezone to run dag
        now = datetime.now().astimezone()
        now_ts = int(round(now.timestamp()))

        dag_run_id = f'{DAG_RUN_ID_PREFIX}-{user_id}-{now_ts}'

        # TODO add meta (user_id, env, etc.)
        dag_run = DAGRun(
            dag_run_id=dag_run_id,
            logical_date=now,
            execution_date=now,
            conf={},
        )

        # TODO check if user has existing dags running and set limit?
        api_response = self.airflow_dag_run_api.post_dag_run(dag_id=dag_name, dag_run=dag_run)
        return api_response['dag_id'], api_response['dag_run_id']

    def _get_dag_name_and_run_id_if_needed(self, user_id: str, dag_name: Optional[str] = None, dag_run_id: Optional[str] = None) -> Tuple[str, str]:
        # TODO asyncify
        # get current dag for user if not provided:
        if dag_name is None:
            confs = self.db_client.select_configs(owner_id=user_id)
            if len(confs) == 0:
                raise RuntimeError(f'User {user_id} has no running dags')
            dag_name = confs[0].dag_name

        # get latest dag_run for user if not provided:
        if dag_run_id is None:
            dag_runs = self.airflow_dag_run_api.get_dag_runs(dag_id=dag_name)['dag_runs']

            # only consider runs with specific naming
            dag_runs = list(filter(lambda r: r['dag_run_id'].startswith(DAG_RUN_ID_PREFIX), dag_runs))
            if len(dag_runs) == 0:
                raise RuntimeError(f'User {user_id} has no dag runs')
            dag_run_id = dag_runs[0]['dag_run_id']

        return dag_name, dag_run_id

    def watch_dag(self, user_id: str, dag_name: Optional[str] = None, dag_run_id: Optional[str] = None) -> Generator:
        dag_name, dag_run_id = self._get_dag_name_and_run_id_if_needed(user_id=user_id, dag_name=dag_name, dag_run_id=dag_run_id)
        prev_dag_run = None
        prev_task_instances = None
        while True:
            # TODO asyncify
            dag_run = self.airflow_dag_run_api.get_dag_run(dag_id=dag_name, dag_run_id=dag_run_id)
            task_instances = self.airflow_task_instance_api.get_task_instances(dag_id=dag_name, dag_run_id=dag_run_id, _check_return_type=False)
            # yield only on difference
            if prev_dag_run != dag_run or prev_task_instances != task_instances:
                prev_dag_run = dag_run
                prev_task_instances = task_instances
                # TODO model for dag state
                res = {k: dag_run[k] for k in ['state', 'start_date', 'end_date', 'execution_date', 'dag_id', 'dag_run_id']}
                res['tasks'] = []
                for t in task_instances['task_instances']:
                    res['tasks'].append({k: t[k] for k in ['task_id', 'state', 'start_date', 'end_date', 'execution_date', 'duration']})

                yield res

            # terminal state
            state = dag_run['state']
            if str(state) in ['success', 'failed']:
                yield f'Dag finished with state: {state}'
                break

            time.sleep(1)

    def watch_task_logs(self, user_id: str, task_name: str, dag_name: Optional[str] = None, dag_run_id: Optional[str] = None, timeout: int = 90) -> Generator:
        dag_name, dag_run_id = self._get_dag_name_and_run_id_if_needed(user_id=user_id, dag_name=dag_name, dag_run_id=dag_run_id)
        continuation_token = None
        while True:
            # TODO asyncify
            # get task state to check if we should continue fetching logs
            task_instance = None
            start_ts = time.time()
            while time.time() - start_ts < timeout:
                try:
                    task_instance = self.airflow_task_instance_api.get_task_instance(dag_id=dag_name, dag_run_id=dag_run_id, task_id=task_name, _check_return_type=False)
                    break
                except:
                    print('Not able to retrieve task instance, retrying...')
                    time.sleep(1)
                    continue
            if task_instance is None:
                yield f'Not able to retrieve task instance after {timeout}s'
                break

            task_state = task_instance['state']

            kwargs = {
                'full_content': continuation_token is None,
            }
            if continuation_token is not None:
                kwargs['token'] = continuation_token

            logs = self.airflow_task_instance_api.get_log(
                dag_id=dag_name,
                dag_run_id=dag_run_id,
                task_id=task_name,
                task_try_number=1,
                **kwargs
            )
            content, new_continuation_token = logs['content'], logs['continuation_token']
            decoded = codecs.escape_decode(bytes(content, 'utf-8'))[0].decode('utf-8')
            # this is a string of [('host', 'logs')] format # TODO parse
            logs = decoded

            if len(decoded) != 0 and continuation_token != new_continuation_token:
                continuation_token = new_continuation_token
                yield logs

            # terminal states
            if task_state in ['success', 'failed', 'upstream_failed', 'shutdown']:
                yield f'Task finished with state: {task_state}'
                break

            time.sleep(1)

    # TODO should be in client module
    @staticmethod
    def preprocess_user_defined_dag_config(user_id: str, dag_conf: Dict) -> Dict:
        REMOTE_CODE_S3_BUCKET = 'svoe-remote-code'
        # all sanitization and client side uploads go here
        # remote_code_local_path code upload:
        for task_id in dag_conf['tasks']:
            task_spec = dag_conf['tasks'][task_id]
            operator = task_spec['operator']
            if 'args' not in task_spec:
                continue
            args = task_spec['args']
            args['user_id'] = user_id
            # TODO sync keys with all remote code operators
            if 'remote_code_local_path' in args:
                remote_code_local_path = args['remote_code_local_path']
                file_name = Path(remote_code_local_path).name
                token = secrets.token_hex(16)
                s3_path = f's3://{REMOTE_CODE_S3_BUCKET}/{user_id}/{operator}/{token}/{file_name}'
                # cleanup previous content for this operator by deleting prefix
                s3_prefix = f'{user_id}/{operator}/'
                # TODO asyncify
                delete_by_prefix(bucket_name=REMOTE_CODE_S3_BUCKET, prefix=s3_prefix) # TODO this doesnt work
                # upload
                upload_dir(s3_path=s3_path, local_path=remote_code_local_path)
                args['_remote_code_remote_path'] = s3_path
        return dag_conf


# TODO remove after testing
if __name__ == '__main__':
    # tempdir, path = download_file('s3://svoe-remote-code/1/svoe_airflow.operators.svoe_python_operator.SvoePythonOperator/5e0d8a6714798ab5138596693e2ec6ab/test_remote_code_v1.py')
    # tempdir.cleanup()
    # print(path)
    runner = DagRunner()
    user_id = '1'
    dag_yaml_path = '../client/dag_runner_client/sample_dag.yaml'
    with open(dag_yaml_path, 'r') as stream:
        dag_conf = yaml.safe_load(stream)
        dag_conf = DagRunner.preprocess_user_defined_dag_config(user_id=user_id, dag_conf=dag_conf)
        runner.run_dag_locally(user_defined_dag_config=dag_conf)
        # dag_name, dag_run_id = runner.run_dag(user_id=user_id, user_defined_dag_config=dag_conf)
        # w1 = runner.watch_dag(user_id=user_id, dag_name=dag_name, dag_run_id=dag_run_id)
        # w2 = runner.watch_task_logs(user_id=user_id, task_name='featurize', dag_name=dag_name, dag_run_id=dag_run_id, timeout=90)
        # print(next(w1))
        # time.sleep(3)
        # for l in w2:
        #     print(l)
    # @ray.remote
    # def ping():
    #     return 'ping'
    #
    # ray_address = 'ray://test-cluster-head-svc.ray-system:10001'
    # local_ray_address = RayClusterManager.port_forward_local(cluster_name='test-cluster')
    # try:
    #     with ray.init(address=local_ray_address, ignore_reinit_error=True):
    #         ping = ray.get(ping.remote())
    #         if ping != 'ping':
    #             print('Unable to verify ray remote function')
    #         else:
    #             print('All good')
    # except Exception as e:
    #     print(f'Unable to connect to cluster at {ray_address}: {e}')
