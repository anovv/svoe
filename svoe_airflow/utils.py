import os
import time
from datetime import datetime, timezone

import yaml
from typing import List, Tuple, Dict

from common.common_utils import base64_decode
from svoe_airflow.db.models import DagConfigEncoded

DEFAULT_DAG_YAML_SUFFIX = '.yaml'


def store_configs_to_yaml_files(confs: List[DagConfigEncoded], dags_folder: str, suffix: str):
    for conf in confs:
        filename = construct_dag_yaml_path(dags_folder, conf.dag_name, suffix)
        dag_config = base64_decode(conf.dag_config_encoded)
        # TODO asyncify this
        with open(filename, 'w') as outfile:
            yaml.dump(dag_config, outfile, default_flow_style=False)


def delete_files(to_delete: List[str]):
    for f in to_delete:
        if os.path.exists(f):
            os.remove(f)


def diff(confs: List[DagConfigEncoded], dags_folder: str, suffix: str) -> Tuple[List[DagConfigEncoded], List[str]]:
    to_add = []
    to_delete = []
    confs_file_names = list(map(lambda e: construct_dag_yaml_path(
        dags_folder=dags_folder,
        dag_name=e.dag_name,
        suffix=suffix
    ), confs))

    # check present files
    on_disc = []
    for file in os.listdir(dags_folder):
        full_path = os.path.join(dags_folder, file)
        if os.path.isfile(full_path) and full_path.endswith(suffix):
            on_disc.append(full_path)

    for f in on_disc:
        if f not in confs_file_names:
            to_delete.append(f)

    for i in range(len(confs_file_names)):
        if confs_file_names[i] not in on_disc:
            to_add.append(confs[i])

    return to_add, to_delete


def sync_configs(confs: List[DagConfigEncoded], dags_folder: str, suffix: str):
    to_add, to_delete = diff(confs=confs, dags_folder=dags_folder, suffix=suffix)
    if len(to_add) > 0:
        store_configs_to_yaml_files(confs=to_add, dags_folder=dags_folder, suffix=suffix)
    if len(to_delete) > 0:
        delete_files(to_delete)


def construct_dag_yaml_path(dags_folder: str, dag_name: str, suffix: str) -> str:
    return f'{dags_folder}/{dag_name}{suffix}'


def dag_name_from_yaml_path(path: str, suffix: str) -> str:
    splits = path.split('/')
    last = splits[len(splits) - 1]
    dag_name = last.removesuffix(suffix)
    return dag_name


# translates user defined dag config to proper Airflow format, generates unqiue name
def user_dag_conf_to_airflow_dag_conf(svoe_dag_conf: Dict, owner_id: str) -> Tuple[str, Dict]:
    # add required by Airflow default_args
    svoe_dag_conf['default_args'] = {
        'owner': 'default',
        'start_date': '1992-09-02'
    }
    svoe_dag_conf['schedule_interval'] = None
    svoe_dag_conf['catchup'] = False
    svoe_dag_conf['is_paused_upon_creation'] = False
    svoe_dag_conf['max_active_runs'] = 1
    now = datetime.now().astimezone(tz=timezone.utc)
    now_ts = int(round(now.timestamp()))
    dag_name = f'dag-{owner_id}-{now_ts}'
    airflow_dag_conf = {
        dag_name: svoe_dag_conf
    }
    return dag_name, airflow_dag_conf
