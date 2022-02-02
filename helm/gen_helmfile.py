# python3

import subprocess
import json
import yaml
import os
import os.path

GLOBAL_HELMFILE_PATH = './helmfile.yaml'
global_helmfile = {'helmfiles': []}

def read_values(release_set_name, chart):
    # chart example: bitnami/metrics-server, contains /
    path = 'release_sets_values/' + release_set_name + '/' + chart + '/values.yaml'

    if not os.path.exists(path):
        print(f'No values file for {chart}')
        return {}

    v = yaml.safe_load(open(path))
    if v is None:
        return {}
    return v

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
    cluster_name = cluster_config['cluster_name']
    helmfile = {'helmDefaults': {
        'kubeContext': cluster_name,
        'recreatePods': True
    }, 'repositories': [], 'releases': []}
    for release_set_name in helm_config['config'][str(cluster_id)]:
        release_set = helm_config['release_sets'][release_set_name]
        for repository in release_set['repositories']:
            helmfile['repositories'].append(repository)
        for release in release_set['releases']:
            r = release.copy()
            r['set'] = []
            values = read_values(release_set_name, release['chart'])
            for k in values:
                # TODO figure out typing for list of values
                r['set'].append({
                    'name': k,
                    'value': values[k]
                })

            # from terraform
            if 'tf_values' in release:
                del r['tf_values']
                for k in release['tf_values']:
                    r['set'].append({
                        'name': k,
                        'value': cluster_config[release['tf_values'][k]]
                    })

            helmfile['releases'].append(r)

    helmfile_path = get_helmfile_path(cluster_name)
    os.makedirs(os.path.dirname(helmfile_path), exist_ok=True)
    with open(helmfile_path, 'w') as helmfile_yaml:
        yaml.dump(helmfile, helmfile_yaml, default_flow_style=False)

    global_helmfile['helmfiles'].append(helmfile_path)

os.makedirs(os.path.dirname(GLOBAL_HELMFILE_PATH), exist_ok=True)
with open(GLOBAL_HELMFILE_PATH, 'w') as global_helmfile_yaml:
    yaml.dump(global_helmfile, global_helmfile_yaml, default_flow_style=False)