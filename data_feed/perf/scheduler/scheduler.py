import time
import concurrent.futures
import functools

from perf.defines import NODE_MEMORY_ALLOC_THRESHOLD, NODE_RESCHEDULE_PERIOD, DATA_FEED_CONTAINER
from perf.estimator.estimator import Estimator
from perf.estimator.estimation_state import PodEstimationPhaseEvent
from perf.kube_api.resource_convert import ResourceConvert


class Scheduler:
    def __init__(self, kube_api, scheduling_state, estimation_state, kube_watcher_state):
        self.kube_api = kube_api
        self.scheduling_state = scheduling_state
        self.estimation_state = estimation_state
        self.kube_watcher_state = kube_watcher_state

        self.estimator = Estimator(self.kube_api, self.estimation_state)
        self.running = False
        self.futures = {}

    def run(self, subset=None):
        self.scheduling_state.init_pods_work_queue(self.kube_api.load_pod_names_from_ss(subset))
        init_work_queue_size = len(self.scheduling_state.pods_work_queue)
        print(f'Scheduling estimation for {init_work_queue_size} pods...')
        # TODO tqdm progress
        self.running = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=1024) as executor:
            while self.running and len(self.scheduling_state.pods_done) != init_work_queue_size:
                self.remove_done_futures()
                pod_name = self.scheduling_state.pop_or_wait_work_queue(self.futures)
                if pod_name is None:
                    self.running = False
                    break

                while (node_name := self.get_ready_node_name()) is None and self.running:
                    time.sleep(1)

                print(f'Scheduling pod {pod_name} on node {node_name}')

                priority = self.scheduling_state.get_schedulable_pod_priority(node_name)
                self.scheduling_state.add_pod_to_schedule_state(pod_name, node_name, priority)
                future = executor.submit(
                    self.estimator.estimate_resources,
                    pod_name=pod_name,
                    node_name=node_name,
                    priority=priority
                )

                future.add_done_callback(functools.partial(self.done_estimation_callback, pod_name=pod_name))
                self.futures[future] = pod_name

        print('Scheduler finished')
        # TODO is this needed
        # for future in concurrent.futures.as_completed(self.futures.keys()):
        #     res = future.result()
        #     print(f'Finished estimating resources for {self.futures[future]}: {res}')

    def remove_done_futures(self):
        for f in list(self.futures.keys()):
            if f.done():
                del self.futures[f]

    def done_estimation_callback(self, future, pod_name):
        print(f'Done {pod_name}')
        success = future.result()
        self.scheduling_state.reschedule_or_complete(pod_name, success)
        if success:
            # TODO add reschedule event to stats on failure?
            self.add_df_events_to_stats(pod_name)
        self.clean_states(pod_name)

    def get_ready_node_name(self):
        nodes = self.kube_api.get_nodes()
        nodes_resource_usage = self.kube_api.get_nodes_resource_usage()
        for node in nodes.items:
            node_name = node.metadata.name
            has_resource_estimator_taint = False
            if node.spec.taints:
                for taint in node.spec.taints:
                    if taint.to_dict()['key'] == 'svoe-role' and taint.to_dict()['value'] == 'resource-estimator':
                        has_resource_estimator_taint = True
                        break
            if not has_resource_estimator_taint:
                continue

            is_ready = False
            for condition in node.status.conditions:
                if condition.type == 'Ready' and condition.status == 'True':
                    is_ready = True
                    break
            if not is_ready:
                continue

            allocatable = node.status.allocatable
            alloc_cpu = ResourceConvert.cpu(allocatable['cpu'])
            alloc_mem = ResourceConvert.memory(allocatable['memory'])

            # TODO add cpu_alloc threshold
            if (int(nodes_resource_usage[node_name]['memory']) / int(alloc_mem)) > NODE_MEMORY_ALLOC_THRESHOLD:
                continue

            # TODO figure out heuristics to dynamically derive BULK_SCHEDULE_SIZE
            BULK_SCHEDULE_SIZE = 2
            if node_name not in self.scheduling_state.pods_per_node or len(self.scheduling_state.pods_per_node) <= BULK_SCHEDULE_SIZE:
                return node_name

            last_pod = self.scheduling_state.get_last_scheduled_pod(node_name)
            # only valid case is if last pod is in active estimation phase,
            # all other phases are temporary before removal
            # also wait NODE_RESCHEDULE_PERIOD s for last pod to run successfully before scheduling more
            phase_event = self.estimation_state.get_last_estimation_phase_event(last_pod)
            if phase_event.type == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN \
                    and time.time() - phase_event.local_time.timestamp() > NODE_RESCHEDULE_PERIOD:
                return node_name

        return None

    def add_df_events_to_stats(self, pod_name):
        events = []
        events.extend(self.kube_watcher_state.event_queues_per_pod[pod_name].queue)
        events.extend(self.estimation_state.estimation_phase_events_per_pod[pod_name])
        events.extend(self.estimation_state.estimation_result_events_per_pod[pod_name])
        events.sort(key=lambda event: event.local_time)
        events = list(
            filter(lambda event: event.container_name is None or event.container_name == DATA_FEED_CONTAINER, events))
        events = list(map(lambda event: str(event), events))
        self.estimation_state.add_events_to_stats(pod_name, events)

    def clean_states(self, pod_name):
        del self.kube_watcher_state.event_queues_per_pod[pod_name]
        del self.estimation_state.estimation_phase_events_per_pod[pod_name]
        del self.estimation_state.estimation_result_events_per_pod[pod_name]

    def stop(self):
        return  # TODO
