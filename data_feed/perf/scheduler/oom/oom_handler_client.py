import threading

MIN_OOM_SCORE_ADJ = -997
MAX_OOM_SCORE_ADJ = 998

MARKED_LOW = 'MARKED_LOW' # marked with low probability deletion by OOMhandler
MARKED_HIGH = 'MARKED_HIGH' # marked with high probability deletion by OOMhandler


# class to work with OOMHandler process in context of parent process
class OOMHandlerClient:
    def __init__(self, oom_handler, scheduling_state):
        self.oom_handler = oom_handler
        self.scheduling_state = scheduling_state
        # TODO use expiring keys?
        self.in_flight_pods = {} # pods which scripts are currently being executed
        self.last_marked_high_pod = None
        self.marking_lock = threading.Lock()
        self.return_loop_thread = threading.Thread(target=self.return_loop)
        self.running = False

    def run(self):
        self.return_loop_thread.start()

    def return_loop(self):
        self.running = True
        self.oom_handler.running.value = 1
        while self.running and bool(self.oom_handler.running.value):
            self.oom_handler.return_wait_event.wait()
            if not bool(self.oom_handler.running.value) or not self.running:
                return
            self.oom_handler.lock.acquire()
            res, exec_time = self.oom_handler.return_queue.get()
            self.handle_oom_score_adj_script_result(res, exec_time)
            self.oom_handler.return_wait_event.clear()
            self.oom_handler.lock.release()

    def notify_pod_started(self, pod):
        print(f'[OOMHandlerClient] Marking pods, triggered by {pod}')
        pods_marking = self.decide_pods_marking(pod)
        self.oom_handler.lock.acquire()
        self.oom_handler.args_queue.put(pods_marking)
        self.oom_handler.args_wait_event.set()
        self.oom_handler.lock.release()

    # decide which pods to mark low/high priority for OOMKiller based on already marked/in_flight pods
    def decide_pods_marking(self, pod):
        self.marking_lock.acquire()
        node = self.scheduling_state.get_node_for_scheduled_pod(pod)
        if node is None:
            raise ValueError(f'[OOMHandlerClient] {pod} is not scheduled on any node')
        res = []

        # verify last_marked_high_pod is not stale
        if self.last_marked_high_pod is not None and \
                self.last_marked_high_pod not in self.scheduling_state.pods_per_node[node]:
            self.last_marked_high_pod = None

        if len(self.in_flight_pods) == 0:
            pod_container, score = self.build_oom_script_args(pod, MARKED_HIGH)
            self.in_flight_pods[pod] = MARKED_HIGH
            res.append((pod_container, score, node))
            if self.last_marked_high_pod is not None:
                pod_container, score = self.build_oom_script_args(self.last_marked_high_pod, MARKED_LOW)
                self.in_flight_pods[self.last_marked_high_pod] = MARKED_LOW
                res.append((pod_container, score, node))
            self.last_marked_high_pod = pod
        else:
            if pod in self.in_flight_pods:
                return res
            has_high = False
            for p in self.in_flight_pods:
                if self.in_flight_pods[p] == MARKED_HIGH:
                    has_high = True
                    break

            mark = MARKED_LOW if has_high else MARKED_HIGH
            pod_container, score = self.build_oom_script_args(pod, mark)
            res.append((pod_container, score, node))
            self.in_flight_pods[pod] = mark
            if mark == MARKED_HIGH:
                self.last_marked_high_pod = pod

        self.marking_lock.release()
        return res

    # create pod_container mapping and score for them
    def build_oom_script_args(self, pod, mark):
        pod_container = {pod: []}
        for container in self.scheduling_state.get_containers_per_pod(pod):
            pod_container[pod].append(container)
        return pod_container, MAX_OOM_SCORE_ADJ if mark == MARKED_HIGH else MIN_OOM_SCORE_ADJ

    def handle_oom_score_adj_script_result(self, res, exec_time):
        if not self.running:
            return
        # returns pids + oom_score_adj
        self.marking_lock.acquire()
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
            print(f'[OOMHandlerClient] Done for {pod} {self.in_flight_pods[pod]} in {exec_time}s')
            del self.in_flight_pods[pod]
        self.marking_lock.release()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.return_loop_thread.join()
