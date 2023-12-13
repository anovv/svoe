# python3

import subprocess
import json
import yaml
import os
import os.path

GLOBAL_HELMFILE_PATH = 'helmfile.yaml'
TEMPLATE_HELMFILE_PATH = 'template.yaml'
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
    for cluster_type in ['minikube', 'remote']:
        if cluster_type == 'minikube':
            cluster_name = 'minikube-' + cluster_id
        elif cluster_type == 'remote':
            cluster_name = tf_config['multicluster_config_output']['value'][cluster_id]['cluster_name']
        else:
            raise ValueError('Unsupported cluster type')

        # set tf values as default env values
        env_values = GLOBAL_ENV_VALUES.copy()
        env_values.update({
            'clusterType': cluster_type,
            'clusterName': cluster_name,
            'clusterId': int(cluster_id),
            'clusterIds': cluster_ids,
            'observerClusterId': OBSERVER_CLUSTER_ID,
            'isObserver': int(cluster_id) == OBSERVER_CLUSTER_ID,
            'isMysqlHost': int(cluster_id) == MYSQL_HOST_CLUSTER_ID,
            'thanosEnabled': False,
        })

        # generate env_values.yaml for each cluster
        env_values_path = get_env_values_per_cluster_path(cluster_name)
        os.makedirs(os.path.dirname(env_values_path), exist_ok=True)
        with open(env_values_path, 'w') as env_values_yaml:
            yaml.dump(env_values, env_values_yaml, default_flow_style=False)

        # copy template for each cluster
        helmfile_path = get_helmfile_per_cluster_path(cluster_name)
        os.makedirs(os.path.dirname(helmfile_path), exist_ok=True)
        os.system(f'cp {TEMPLATE_HELMFILE_PATH} {helmfile_path}')

        if cluster_type != 'minikube':
            # ignore minikube for global helmfile (or make separate?)
            GLOBAL_HELMFILE['helmfiles'].append(helmfile_path)

os.makedirs(os.path.dirname(GLOBAL_HELMFILE_PATH), exist_ok=True)
with open(GLOBAL_HELMFILE_PATH, 'w') as global_helmfile_yaml:
    yaml.dump(GLOBAL_HELMFILE, global_helmfile_yaml, default_flow_style=False)