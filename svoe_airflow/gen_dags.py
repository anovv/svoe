import datetime
import traceback

from dagfactory import load_yaml_dags, DagFactory
from airflow.configuration import conf as airflow_conf
from svoe_airflow.db.dags_mysql_client import DagsMysqlClient
from svoe_airflow.utils import DEFAULT_DAG_YAML_SUFFIX, sync_configs, dag_name_from_yaml_path
from pathlib import Path

print(f'[gen_dags.py] Called at {datetime.datetime.now()}')
dags_folder = airflow_conf.get('core', 'dags_folder')
suffix = DEFAULT_DAG_YAML_SUFFIX # '.yaml'

client = DagsMysqlClient()
confs = client.select_all_configs()

# only sync confs without compilation errors
confs = list(filter(lambda conf: conf.compilation_error is None, confs))

sync_configs(confs=confs, dags_folder=dags_folder, suffix=suffix)

# load_yaml_dags(globals_dict=globals(), dags_folder=dags_folder, suffix=[suffix])
globals_dict = globals()
candidate_dag_files = Path(dags_folder).rglob(f"*{suffix}")
for config_file_path in candidate_dag_files:
    config_file_abs_path = str(config_file_path.absolute())
    try:
        DagFactory(config_file_abs_path).generate_dags(globals_dict)
    except Exception as e:
        exception_trace = traceback.format_exc()
        print(f'[gen_dags.py] Can not generate dag {config_file_path}')
        try:
            dag_name = dag_name_from_yaml_path(config_file_abs_path, suffix=suffix)

            # TODO asyncify this
            client.report_compilation_error(dag_name=dag_name, error=exception_trace)
        except:
            # in case path is not parsable, nothing we can do with this dag, it is a zombie
            # TODO possibly parse yaml itself and derive dag_name from there? Too much work at the moment
            pass
print(f'[gen_dags.py] Sync done at {datetime.datetime.now()}')

