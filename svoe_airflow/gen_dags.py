from dagfactory import load_yaml_dags
from airflow.configuration import conf as airflow_conf
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient
from svoe_airflow.utils import DEFAULT_DAG_YAML_SUFFIX, sync_configs

dags_folder = airflow_conf.get('core', 'dags_folder')
suffix = DEFAULT_DAG_YAML_SUFFIX # '.yaml'

client = DagsMysqlClient()
confs = client.select_all_configs()

sync_configs(confs=confs, dags_folder=dags_folder, suffix=suffix)

load_yaml_dags(globals_dict=globals(), dags_folder=dags_folder, suffix=[suffix])
