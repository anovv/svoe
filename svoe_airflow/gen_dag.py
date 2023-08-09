from airflow.utils import yaml
from dagfactory import load_yaml_dags
from airflow.configuration import conf as airflow_conf
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient

dags_folder = airflow_conf.get('core', 'dags_folder')
client = DagsMysqlClient()
confs = client.select_all_configs()
for (owner_id, dag_name, config) in confs:
    filename = f'{owner_id}-{dag_name}.yaml'
    # TODO asyncify this
    with open('filename', 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)

load_yaml_dags(globals_dict=globals(), dags_folder=dags_folder, suffix=['.yaml'])
