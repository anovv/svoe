import os

import yaml
from typing import List, Tuple

from common.common_utils import base64_decode
from svoe_airflow.db.models import DagConfigEncoded

DEFAULT_DAG_YAML_SUFFIX = '.yaml'


def store_configs_to_yaml_files(confs: List[DagConfigEncoded], dags_folder: str, suffix: str):
    for conf in confs:
        filename = construct_dag_yaml_path(dags_folder, conf.owner_id, conf.dag_name, suffix)
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
        owner_id=e.owner_id,
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


def construct_dag_yaml_path(dags_folder: str, owner_id: str, dag_name: str, suffix: str) -> str:
    return f'{dags_folder}/{owner_id}-{dag_name}{suffix}'
