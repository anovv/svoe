import threading

from perf.defines import DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER
from perf.scheduler.oom.oom_scripts_utils import set_oom_score_adj

MIN_OOM_SCORE_ADJ = -1000
MAX_OOM_SCORE_ADJ = 1000


class OOMHandler:
    def __init__(self, scheduling_state):
        self.scheduling_state = scheduling_state

    def _get_containers_per_pod(self, pod):
        # TODO make this dynamic
        return [DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER]

    def try_get_pids_and_set_oom_score_adj(self, pod):
        # For newly launched pod sets highest possible oom_score_adj for all processes inside
        # all containers in this pod (soo oomkiller picks it's processes first) and
        # gets back list of pids inside of all containers in this pod.
        # In the same call, sets lowest oom_score_adj for previously launched pod's processes.
        # This should be called after making sure all appropriate containers have started/passed probes
        script_args = {pod: {}}
        for container in self._get_containers_per_pod(pod):
            script_args[pod][container] = MAX_OOM_SCORE_ADJ
        node = self.scheduling_state.get_node_for_scheduled_pod(pod)
        last_pod = self.scheduling_state.get_last_scheduled_pod(node)
        if last_pod is not None:
            script_args[last_pod] = {}
            for container in self._get_containers_per_pod(last_pod):
                script_args[last_pod][container] = MIN_OOM_SCORE_ADJ
        threading.Thread(target=self._set_oom_score_adj_blocking, args=(script_args, node)).start()

    def _set_oom_score_adj_blocking(self, script_args, node):
        # TODO try/except ?
        # TODO add scheduling events?
        res = set_oom_score_adj(script_args, node)
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
