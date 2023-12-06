import subprocess
import os


def construct_containers_script_param(pod_container):
    c_arg = ""
    for pod in pod_container:
        for container in pod_container[pod]:
            c_arg += f'{container}_{pod} '

    return c_arg.strip()


def parse_output(output):
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


def parse_script_and_replace_param_vars(tmpl, params):
    for param_name in params:
        tmpl = tmpl.replace(f'{param_name}=""', f'{param_name}="{params[param_name]}"')
    return tmpl


def _exec_node_shell_cmd_DEPRECATED(cmd):
    env = os.environ.copy()
    # env['KUBECTL_NODE_SHELL_POD_CPU'] = KUBECTL_NODE_SHELL_POD_CPU
    # env['KUBECTL_NODE_SHELL_POD_MEMORY'] = KUBECTL_NODE_SHELL_POD_MEMORY

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout, _ = process.communicate()
    return parse_output(stdout.decode("utf-8"))