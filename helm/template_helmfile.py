# python3

import subprocess
import json
import yaml
import os
import os.path

GLOBAL_HELMFILE_PATH = './helmfile.yaml'
TEMPLATE_HELMFILE_PATH = './template.yaml'
GLOBAL_HELMFILE = {'helmfiles': []}
OBSERVER_CLUSTER_ID = 1
MYSQL_HOST_CLUSTER_ID = 1

def get_helmfile_per_cluster_path(cluster_name):
    return 'helmfiles_gen/' + cluster_name + '/helmfile.yaml'

def get_env_values_per_cluster_path(cluster_name):
    return 'helmfiles_gen/' + cluster_name + '/env_values.yaml'

tf = subprocess.getoutput('cd ../terraform && terraform output -json')
tf_config = json.loads(tf)

GLOBAL_ENV_VALUES = {
    'dataFeedImagePrefix': tf_config['svoe_data_feed_ecr_repo_url']['value']
}

cluster_ids = [int(cluster_id) for cluster_id in tf_config['multicluster_config_output']['value']]

for cluster_id in tf_config['multicluster_config_output']['value']:
    cluster_config = tf_config['multicluster_config_output']['value'][cluster_id]

    # set tf values as default env values
    cluster_name = cluster_config['cluster_name']
    env_values = GLOBAL_ENV_VALUES.copy()
    env_values.update({
        'clusterName': cluster_name,
        'clusterId': int(cluster_id),
        'clusterIds': cluster_ids,
        'observerClusterId': OBSERVER_CLUSTER_ID,
        'isObserver': int(cluster_id) == OBSERVER_CLUSTER_ID,
        'isMysqlHost': int(cluster_id) == MYSQL_HOST_CLUSTER_ID,
    })

    env_values_path = get_env_values_per_cluster_path(cluster_name)
    os.makedirs(os.path.dirname(env_values_path), exist_ok=True)
    with open(env_values_path, 'w') as env_values_yaml:
        yaml.dump(env_values, env_values_yaml, default_flow_style=False)

    helmfile_path = get_helmfile_per_cluster_path(cluster_name)
    os.makedirs(os.path.dirname(helmfile_path), exist_ok=True)
    os.system(f'cp {TEMPLATE_HELMFILE_PATH} {helmfile_path}')
    GLOBAL_HELMFILE['helmfiles'].append(helmfile_path)

os.makedirs(os.path.dirname(GLOBAL_HELMFILE_PATH), exist_ok=True)
with open(GLOBAL_HELMFILE_PATH, 'w') as global_helmfile_yaml:
    yaml.dump(GLOBAL_HELMFILE, global_helmfile_yaml, default_flow_style=False)