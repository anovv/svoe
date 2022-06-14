import subprocess
import pathlib
import os

KUBECTL_NODE_SHELL_POD_CPU = "30m"
KUBECTL_NODE_SHELL_POD_MEMORY = "30Mi"


# set_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': '-1000'}}, 'minikube-1-m03')
def set_oom_score_adj(pod_container_score, node):
    c_arg, s_arg = _construct_script_params(pod_container_score)
    path = pathlib.Path(__file__).parent.resolve()
    cmd = [f'{path}/scripts/set_containers_oom_score_adj.sh', f'-c "{c_arg}"', f'-s "{s_arg}"', f'-n {node}']
    return _exec_node_shell_cmd(cmd)

# get_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': None}}, 'minikube-1-m03')
def get_oom_score(pod_container, node):
    c_arg, _ = _construct_script_params(pod_container)
    path = pathlib.Path(__file__).parent.resolve()
    cmd = [f'{path}/scripts/get_containers_oom_score.sh', f'-c "{c_arg}"', f'-n {node}']
    return _exec_node_shell_cmd(cmd)

def _construct_script_params(pod_container_score_adj):
    c_arg = ""
    s_arg = ""
    for pod in pod_container_score_adj:
        for container in pod_container_score_adj[pod]:
            oom_score_adj = pod_container_score_adj[pod][container]
            c_arg += f'{container}_{pod} '
            if oom_score_adj is not None:
                s_arg += f'{oom_score_adj} '

    return c_arg.strip(), s_arg.strip()

def _exec_node_shell_cmd(cmd):
    env = os.environ.copy()
    env['KUBECTL_NODE_SHELL_POD_CPU'] = KUBECTL_NODE_SHELL_POD_CPU
    env['KUBECTL_NODE_SHELL_POD_MEMORY'] = KUBECTL_NODE_SHELL_POD_MEMORY

    process = subprocess.Popen(
        # [f'{path}/scripts/get_containers_oom_score.sh', f'-c "data-feed-container_data-feed-binance-spot-6d1641b134"', '-n minikube-1-m03'],
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout, _ = process.communicate()
    return _parse_output(stdout.decode("utf-8"))

def _parse_output(output):
    res = {}
    split1 = output.split('\n')
    for s in split1:
        split2 = s.split(',')
        if len(split2) < 2:
            continue
        container_pod = None
        pid = None
        oom_score = None
        oom_score_adj = None
        for ss in split2:
            split3 = ss.split(':')
            key = split3[0].strip()
            value = split3[1].strip()
            if value == 'None':
                value = None
            if key == 'container':
                container_pod = value
            elif key == 'pid':
                pid = value
            elif key == 'oom_score':
                oom_score = value
            elif key == 'oom_score_adj':
                oom_score_adj = value
            else:
                raise Exception(f'unknown key {key}')
        if container_pod is None or pid is None:
            raise Exception(f'container name or pid is None')
        split4 = container_pod.split('_')
        container = split4[0]
        pod = split4[1]

        if pod in res:
            if container in res[pod]:
                res[pod][container][pid] = (oom_score, oom_score_adj)
            else:
                res[pod][container] = {pid: (oom_score, oom_score_adj)}
        else:
            res[pod] = {container: {pid: (oom_score, oom_score_adj)}}
    return res

print(set_oom_score_adj({'data-feed-binance-spot-6d1641b134': {'data-feed-container': -1000}}, 'minikube-1-m03'))