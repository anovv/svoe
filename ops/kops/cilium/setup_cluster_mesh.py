# python3

import subprocess
import json
import time
from itertools import combinations


cilium_multicluster_config = {}

def get_cilium_cluster_name(cluster_id, vpc_name):
    # cilium does not support dot notations so we have to create a unique cluster name here
    # vpc_name-cluster_id
    return vpc_name + '-' + cluster_id


p = subprocess.getoutput('cd ../../terraform && terraform output -json')
obj = json.loads(p)

for cluster_id in obj['multicluster_config_output']['value']:
    # cilium_multicluster_config[cluster_id] = {'cluster_name': cluster_config['cluster_name'] }
    cluster_config = obj['multicluster_config_output']['value'][cluster_id]
    cluster_name = cluster_config['cluster_name']
    cilium_cluster_name = get_cilium_cluster_name(cluster_id, cluster_config['vpc_name'])
    cilium_multicluster_config[cluster_id] = cluster_name
    exe = f'kubectl config use-context {cluster_name} && cilium config set cluster-id {cluster_id} && cilium config set cluster-name {cilium_cluster_name}'
    out = subprocess.getoutput(exe)
    print(out)

for cluster_id in cilium_multicluster_config:
    cluster_name = cilium_multicluster_config[cluster_id]
    exe = f'cilium clustermesh enable --context {cluster_name} --service-type NodePort'
    out = subprocess.getoutput(exe)
    print(out)

for cluster_id in cilium_multicluster_config:
    cluster_name = cilium_multicluster_config[cluster_id]
    exe = f'cilium clustermesh status --context {cluster_name} --wait --wait-duration 30s'
    out = subprocess.getoutput(exe)
    print(out)

pairs = [pair for pair in combinations(cilium_multicluster_config.keys(), 2)]
for pair in pairs:
    cluster_name1 = cilium_multicluster_config[pair[0]]
    cluster_name2 = cilium_multicluster_config[pair[1]]
    exe = f'cilium clustermesh connect --context {cluster_name1} --destination-context {cluster_name2}'
    out = subprocess.getoutput(exe)
    print(out)

time.sleep(4) # just in case

print('Restarting cilium pods...')
for cluster_id in obj['multicluster_config_output']['value']:
    exe = f'./restart_cilium_pods.sh {cluster_id}'
    out = subprocess.getoutput(exe)
    print(out)

print('Done.')

