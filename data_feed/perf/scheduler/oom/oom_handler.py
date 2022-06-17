import threading
import multiprocessing
import time
import pathlib

from perf.kube_api.kube_api import KubeApi
from perf.scheduler.oom.oom_scripts_utils import construct_script_params, parse_output, parse_script_and_replace_param_vars

MIN_OOM_SCORE_ADJ = -998
MAX_OOM_SCORE_ADJ = 998


# should be a separate process with it's own instance of kuberenetes.client and core_api
# so we have no interference with main process' client
# so we have no interference with main process' client
class OOMHandler(multiprocessing.Process):
    def __init__(self):
        super().__init__()
        self.kube_api = None
        self.running = multiprocessing.Value('i', 0)
        self.args_wait_event = multiprocessing.Event()
        self.args_queue = multiprocessing.Queue()
        self.return_wait_event = multiprocessing.Event()
        self.return_queue = multiprocessing.Queue()
        self.lock = multiprocessing.Lock()

    # caller process context
    def return_loop(self, scheduling_state):
        self.running.value = 1
        while bool(self.running.value):
            self.return_wait_event.wait()
            if not bool(self.running.value):
                return
            self.lock.acquire()
            res = self.return_queue.get()
            OOMHandler.handle_oom_score_adj_script_result(scheduling_state, res)
            self.return_wait_event.clear()
            self.lock.release()

    # caller process context
    def notify_oom_event(self, scheduling_state, pod):
        args, node = OOMHandler.build_oom_script_args(scheduling_state, pod)
        self.lock.acquire()
        self.args_queue.put((args, node))
        self.args_wait_event.set()
        self.lock.release()

    def run(self):
        print('OOMHandler started')
        # OOMHandler should have it's own instance of KubeApi set inside it's process context
        self.kube_api = KubeApi.new_instance()
        self.running.value = 1
        while bool(self.running.value):
            self.args_wait_event.wait()
            if not bool(self.running.value):
                return
            self.lock.acquire()
            script_args, node = self.args_queue.get()
            self._try_get_pids_and_set_oom_score_adj(script_args, node)
            self.args_wait_event.clear()
            self.lock.release()

    def stop(self):
        self.running.value = 0
        if not self.args_wait_event.is_set():
            self.args_wait_event.set()
        if not self.return_wait_event.is_set():
            self.return_wait_event.set()

    def _try_get_pids_and_set_oom_score_adj(self, script_args, node):
        # For newly launched pod sets highest possible oom_score_adj for all processes inside
        # all containers in this pod (so oomkiller picks these processes first) and
        # gets back list of pids inside of all containers in this pod.
        # In the same call, sets lowest oom_score_adj for previously launched pod's processes.
        # This should be called after making sure all appropriate containers have started/passed probes
        # TODO use executor
        threading.Thread(target=self._set_oom_score_adj_blocking, args=(script_args, node)).start()

    def _set_oom_score_adj_blocking(self, script_args, node):
        # TODO try/except ?
        # TODO add scheduling events?
        # TODO self.runnning checks
        start = time.time()
        res = self.set_oom_score_adj(script_args, node)
        self.lock.acquire()
        self.return_queue.put(res)
        self.return_wait_event.set()
        self.lock.release()
        print(f'Done oom_score_adj in {time.time() - start}s, res: {res}')

    @staticmethod
    def handle_oom_score_adj_script_result(scheduling_state, res):
        # returns pids + oom_score_adj
        print(f'Handling oom_score_adj_script_result')
        for pod in res:
            for container in res[pod]:
                for pid in res[pod][container]:
                    oom_score = res[pod][container][pid][0] # script always returns None for this
                    oom_score_adj = res[pod][container][pid][1]
                    if pod in scheduling_state.pids_per_container_per_pod:
                        if container in scheduling_state.pids_per_container_per_pod[pod]:
                            scheduling_state.pids_per_container_per_pod[pod][container][pid] = (oom_score, oom_score_adj)
                        else:
                            scheduling_state.pids_per_container_per_pod[pod][container] = {pid: (oom_score, oom_score_adj)}
                    else:
                        scheduling_state.pids_per_container_per_pod[pod] = {container: {pid: (oom_score, oom_score_adj)}}
        print(f'oom pids: {scheduling_state.pids_per_container_per_pod}')

    @staticmethod
    def build_oom_script_args(scheduling_state, pod):
        script_args = {pod: {}}
        for container in scheduling_state.get_containers_per_pod(pod):
            script_args[pod][container] = MAX_OOM_SCORE_ADJ
        node = scheduling_state.get_node_for_scheduled_pod(pod)
        if node is None:
            raise ValueError(f'Pod {pod} is not scheduled on any node')
        last_pod = scheduling_state.get_last_scheduled_pod(node)
        if last_pod is not None:
            # TODO what if bulk_schedule?
            script_args[last_pod] = {}
            for container in scheduling_state.get_containers_per_pod(last_pod):
                script_args[last_pod][container] = MIN_OOM_SCORE_ADJ

        print(f'[{pod}]Built oom_score_adj args: {script_args}')
        return script_args, node

    # set_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': -1000}}, 'minikube-1-m03')
    def set_oom_score_adj(self, pod_container_score, node):
        c_arg, s_arg = construct_script_params(pod_container_score)
        path = pathlib.Path(__file__).parent.resolve()
        tmpl = pathlib.Path(f'{path}/scripts/set_containers_oom_score_adj.sh').read_text()
        tmpl = parse_script_and_replace_param_vars(tmpl, {'OOM_SCORES_ADJ_PARAM': s_arg, 'CONTAINERS_PARAM': c_arg})
        res = self.kube_api.execute_remote_script(tmpl, node)
        print(f'Raw res: {res}')
        return parse_output(res)

    # get_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': None}}, 'minikube-1-m03')
    def get_oom_score(self, pod_container, node):
        c_arg, _ = construct_script_params(pod_container)
        path = pathlib.Path(__file__).parent.resolve()
        tmpl = pathlib.Path(f'{path}/scripts/get_containers_oom_score.sh').read_text()
        tmpl = parse_script_and_replace_param_vars(tmpl, {'CONTAINERS_PARAM': c_arg})
        res = self.kube_api.execute_remote_script(tmpl, node)
        return parse_output(res)


