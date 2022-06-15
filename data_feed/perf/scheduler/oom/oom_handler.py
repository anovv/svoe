import threading
import time
import pathlib
import kubernetes
import json

from perf.scheduler.oom.oom_scripts_utils import construct_script_params, parse_output, parse_script_and_replace_param_vars

MIN_OOM_SCORE_ADJ = -1000
MAX_OOM_SCORE_ADJ = 1000
REMOTE_SCRIPTS_DS_CONTAINER = 'remote-scripts-runner'
REMOTE_SCRIPTS_DS_NAME = 'remote-scripts-ds'
REMOTE_SCRIPTS_DS_NAMESPACE = 'kube-system'


class OOMHandler:
    def __init__(self, kube_api, scheduling_state):
        self.kube_api = kube_api
        self.scheduling_state = scheduling_state
        self.remote_scripts_ds_pod_cache = {}

    def try_get_pids_and_set_oom_score_adj(self, pod):
        # For newly launched pod sets highest possible oom_score_adj for all processes inside
        # all containers in this pod (so oomkiller picks these processes first) and
        # gets back list of pids inside of all containers in this pod.
        # In the same call, sets lowest oom_score_adj for previously launched pod's processes.
        # This should be called after making sure all appropriate containers have started/passed probes
        script_args = {pod: {}}
        for container in self.scheduling_state.get_containers_per_pod(pod):
            script_args[pod][container] = MAX_OOM_SCORE_ADJ
        node = self.scheduling_state.get_node_for_scheduled_pod(pod)
        if node is None:
            raise ValueError(f'Pod {pod} is not scheduled on any node')
        last_pod = self.scheduling_state.get_last_scheduled_pod(node)
        if last_pod is not None:
            # TODO what if bulk_schedule?
            script_args[last_pod] = {}
            for container in self.scheduling_state.get_containers_per_pod(last_pod):
                script_args[last_pod][container] = MIN_OOM_SCORE_ADJ
        threading.Thread(target=self._set_oom_score_adj_blocking, args=(script_args, node)).start()

    def _set_oom_score_adj_blocking(self, script_args, node):
        # TODO try/except ?
        # TODO add scheduling events?
        # returns pids + oom_score_adj
        print(f'Setting oom_score_adj args: {script_args}')
        start = time.time()
        res = self.set_oom_score_adj(script_args, node)
        for pod in res:
            for container in res[pod]:
                for pid in res[pod][container]:
                    oom_score = res[pod][container][pid][0] # script always returns None for this
                    oom_score_adj = res[pod][container][pid][1]
                    if pod in self.scheduling_state.pids_per_container_per_pod:
                        if container in self.scheduling_state.pids_per_container_per_pod[pod]:
                            self.scheduling_state.pids_per_container_per_pod[pod][container][pid] = (oom_score, oom_score_adj)
                        else:
                            self.scheduling_state.pids_per_container_per_pod[pod][container] = {pid: (oom_score, oom_score_adj)}
                    else:
                        self.scheduling_state.pids_per_container_per_pod[pod] = {container: {pid: (oom_score, oom_score_adj)}}

        print(f'Done oom_score_adj in {time.time() - start}s, res: {res}, pids: {self.scheduling_state.pids_per_container_per_pod}')

    # set_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': -1000}}, 'minikube-1-m03')
    def set_oom_score_adj(self, pod_container_score, node):
        c_arg, s_arg = construct_script_params(pod_container_score)
        path = pathlib.Path(__file__).parent.resolve()
        tmpl = pathlib.Path(f'{path}/scripts/set_containers_oom_score_adj.sh').read_text()
        tmpl = parse_script_and_replace_param_vars(tmpl, {'OOM_SCORES_ADJ_PARAM': s_arg, 'CONTAINERS_PARAM': c_arg})
        res = self.execute_remote_script(tmpl, node)
        return parse_output(res)

    # get_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': None}}, 'minikube-1-m03')
    def get_oom_score(self, pod_container, node):
        c_arg, _ = construct_script_params(pod_container)
        path = pathlib.Path(__file__).parent.resolve()
        tmpl = pathlib.Path(f'{path}/scripts/get_containers_oom_score.sh').read_text()
        tmpl = parse_script_and_replace_param_vars(tmpl, {'CONTAINERS_PARAM': c_arg})
        res = self.execute_remote_script(tmpl, node)
        return parse_output(res)

    def execute_remote_script(self, script_string, node_name):
        cmd = ['nsenter', '--mount=/proc/1/ns/mnt', '--', 'bash', '-c', script_string]
        if node_name not in self.remote_scripts_ds_pod_cache:
            print(f'[OOMHandler] Stale cache for remote-scripts-ds pod, updating...')
            self.remote_scripts_ds_pod_cache[node_name] = self._get_remote_scripts_pod(node_name)
        remote_scripts_pod = self.remote_scripts_ds_pod_cache[node_name]
        try:
            return self.kube_api.pod_exec(
                REMOTE_SCRIPTS_DS_NAMESPACE,
                remote_scripts_pod,
                REMOTE_SCRIPTS_DS_CONTAINER,
                cmd
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.reason == 'Handshake status 404 Not Found':
                # cache stale, ask kube for latest remote-scripts-ds pod
                print(f'[OOMHandler] Stale cache for remote-scripts-ds pod, updating...')
                remote_scripts_pod = self._get_remote_scripts_pod(node_name)
                self.remote_scripts_ds_pod_cache[node_name] = remote_scripts_pod
                return self.kube_api.pod_exec(
                    REMOTE_SCRIPTS_DS_NAMESPACE,
                    remote_scripts_pod,
                    REMOTE_SCRIPTS_DS_CONTAINER,
                    cmd
                )
            else:
                raise e

    def _get_remote_scripts_pod(self, node_name):
        res = self.kube_api.core_api.list_namespaced_pod(
            namespace=REMOTE_SCRIPTS_DS_NAMESPACE,
            field_selector=f'spec.nodeName={node_name}',
            label_selector='app=remote-scripts',
        )
        try:
            return res.items[0].metadata.name
        except Exception as e:
            print(f'[OOMHandler] Unable to get remote-scripts-ds pod for node {node_name}')
            raise e
