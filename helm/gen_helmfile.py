# python3

import subprocess
import json
import yaml
import os
import os.path

GLOBAL_HELMFILE_PATH = './helmfile.yaml'
global_helmfile = {'helmfiles': []}

def get_values_path(release_set_name, chart):
    # chart example: bitnami/metrics-server, contains /
    return '../../release_sets_values/' + release_set_name + '/' + chart + '/values.yaml.gotmpl'

def get_helmfile_path(cluster_name):
    return 'helmfiles_gen/' + cluster_name + '/helmfile.yaml'

tf = subprocess.getoutput('cd ../terraform && terraform output -json')
tf_config = json.loads(tf)

with open('helm-config.json') as json_file:
    helm_config = json.load(json_file)

for cluster_id in tf_config['multicluster_config_output']['value']:
    if str(cluster_id) not in helm_config['config']:
        continue
    cluster_config = tf_config['multicluster_config_output']['value'][cluster_id]

    # set tf values as default env values
    cluster_name = cluster_config['cluster_name']
    env_vals = [
        {'clusterName': cluster_name},
        {'clusterId': cluster_id}
    ]

    helmfile = {'helmDefaults': {
        'kubeContext': cluster_name,
    }, 'repositories': [], 'releases': [], 'environments': {'default': {'values': env_vals}}}

    # TODO add labels
    for release_set_name in helm_config['config'][str(cluster_id)]:
        release_set = helm_config['release_sets'][release_set_name]
        for repository in release_set['repositories']:
            helmfile['repositories'].append(repository)
        for release in release_set['releases']:
            release['values'] = [get_values_path(release_set_name, release['chart'])]
            helmfile['releases'].append(release)

    helmfile_path = get_helmfile_path(cluster_name)
    os.makedirs(os.path.dirname(helmfile_path), exist_ok=True)
    with open(helmfile_path, 'w') as helmfile_yaml:
        yaml.dump(helmfile, helmfile_yaml, default_flow_style=False)

    global_helmfile['helmfiles'].append(helmfile_path)

os.makedirs(os.path.dirname(GLOBAL_HELMFILE_PATH), exist_ok=True)
with open(GLOBAL_HELMFILE_PATH, 'w') as global_helmfile_yaml:
    yaml.dump(global_helmfile, global_helmfile_yaml, default_flow_style=False)