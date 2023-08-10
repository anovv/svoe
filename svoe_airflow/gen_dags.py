from dagfactory import load_yaml_dags
from airflow.configuration import conf as airflow_conf
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient
from svoe_airflow.utils import store_configs_to_yaml_files, DEFAULT_DAG_YAML_SUFFIX

dags_folder = airflow_conf.get('core', 'dags_folder')
suffix = DEFAULT_DAG_YAML_SUFFIX # '.yaml'

client = DagsMysqlClient()
confs = client.select_all_configs()

# TODO we should store only diff between whats in DB and whats on disk
store_configs_to_yaml_files(confs=confs, dags_folder=dags_folder, suffix=suffix)

# TODO we should also remove dags which are not in DB
load_yaml_dags(globals_dict=globals(), dags_folder=dags_folder, suffix=[suffix])
