import threading
import multiprocessing
import time
import pathlib

from perf.kube_api.kube_api import KubeApi
from perf.scheduler.oom.oom_scripts_utils import construct_script_params, parse_output, parse_script_and_replace_param_vars


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
            self.try_get_pids_and_set_oom_score_adj(script_args, node)
            self.args_wait_event.clear()
            self.lock.release()

    def stop(self):
        self.running.value = 0
        if not self.args_wait_event.is_set():
            self.args_wait_event.set()
        if not self.return_wait_event.is_set():
            self.return_wait_event.set()

    def try_get_pids_and_set_oom_score_adj(self, script_args, node):
        # For newly launched pod sets highest possible oom_score_adj for all processes inside
        # all containers in this pod (so oomkiller picks these processes first) and
        # gets back list of pids inside of all containers in this pod.
        # In the same call, sets lowest oom_score_adj for previously launched pod's processes.
        # This should be called after making sure all appropriate containers have started/passed probes
        # TODO use executor
        threading.Thread(target=self.set_oom_score_adj_blocking, args=(script_args, node)).start()

    def set_oom_score_adj_blocking(self, script_args, node):
        # TODO try/except ?
        # TODO remove pods from in-flight in case of exception
        # TODO add scheduling events?
        start = time.time()
        res = self.set_oom_score_adj(script_args, node)
        exec_time = time.time() - start
        self.lock.acquire()
        self.return_queue.put((res, exec_time))
        self.return_wait_event.set()
        self.lock.release()

    # set_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': -1000}}, 'minikube-1-m03')
    def set_oom_score_adj(self, pod_container_score, node):
        c_arg, s_arg = construct_script_params(pod_container_score)
        path = pathlib.Path(__file__).parent.resolve()
        tmpl = pathlib.Path(f'{path}/scripts/set_containers_oom_score_adj.sh').read_text()
        tmpl = parse_script_and_replace_param_vars(tmpl, {'OOM_SCORES_ADJ_PARAM': s_arg, 'CONTAINERS_PARAM': c_arg})
        res = self.kube_api.execute_remote_script(tmpl, node)
        return parse_output(res)

    # get_oom_score({'data-feed-binance-spot-6d1641b134': {'data-feed-container': None}}, 'minikube-1-m03')
    def get_oom_score(self, pod_container, node):
        c_arg, _ = construct_script_params(pod_container)
        path = pathlib.Path(__file__).parent.resolve()
        tmpl = pathlib.Path(f'{path}/scripts/get_containers_oom_score.sh').read_text()
        tmpl = parse_script_and_replace_param_vars(tmpl, {'CONTAINERS_PARAM': c_arg})
        res = self.kube_api.execute_remote_script(tmpl, node)
        return parse_output(res)
