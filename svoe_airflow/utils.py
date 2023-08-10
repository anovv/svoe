import yaml
from typing import List

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


def construct_dag_yaml_path(dags_folder: str, owner_id: str, dag_name: str, suffix: str) -> str:
    return f'{dags_folder}/{owner_id}-{dag_name}{suffix}'
