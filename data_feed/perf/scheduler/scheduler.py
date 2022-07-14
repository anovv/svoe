import time
import concurrent.futures
import functools
import kubernetes
import json

from perf.defines import NODE_NEXT_SCHEDULE_PERIOD, NODE_MEMORY_ALLOC_THRESHOLD, BULK_SCHEDULE_SIZE
from perf.estimator.estimator import Estimator
from perf.state.phase_result_scheduling_state import PodSchedulingResultEvent, PodSchedulingPhaseEvent, SchedulingTimeouts
from perf.state.estimation_state import PodEstimationPhaseEvent, PodEstimationResultEvent
from perf.kube_api.resource_convert import ResourceConvert
from perf.kube_api.utils import cm_name_pod_name
from perf.scheduler.oom.oom_handler import OOMHandler
from perf.scheduler.oom.oom_handler_client import OOMHandlerClient
from perf.utils import local_now


# explanations for node state (schedulable or not)
class NodeStateReason:
    # schedulable reasons
    SCHEDULABLE_BULK = 'SCHEDULABLE_BULK'
    SCHEDULABLE_SEQUENCE = 'SCHEDULABLE_SEQUENCE'

    # unschedulable reasons
    NO_RESOURCE_ESTIMATOR_LABEL = 'NO_RESOURCE_ESTIMATOR_LABEL'
    NOT_READY = 'NOT_READY'
    NOT_ENOUGH_CPU = 'NOT_ENOUGH_CPU'
    NOT_ENOUGH_MEMORY = 'NOT_ENOUGH_MEMORY'
    LAST_POD_NOT_APPEARED = 'LAST_POD_NOT_APPEARED'
    LAST_POD_NOT_IN_ESTIMATING_STATE = 'LAST_POD_NOT_IN_ESTIMATING_STATE'
    NOT_ENOUGH_TIME_SINCE_LAST_POD_STARTED_ESTIMATION = 'NOT_ENOUGH_TIME_SINCE_LAST_POD_STARTED_ESTIMATION'
    RESOURCES_METRICS_NOT_FRESH_SINCE_OOM_EVENT = 'RESOURCES_METRICS_NOT_FRESH_SINCE_OOM_EVENT'
    RESOURCES_METRICS_NOT_FRESH_SINCE_LAST_POD_STARTED_ESTIMATION = 'RESOURCES_METRICS_NOT_FRESH_SINCE_LAST_POD_STARTED_ESTIMATION'


class Scheduler:
    def __init__(self, kube_api, scheduling_state, estimation_state, kube_watcher_state, stats):
        self.kube_api = kube_api
        self.scheduling_state = scheduling_state
        self.estimation_state = estimation_state
        self.kube_watcher_state = kube_watcher_state

        self.stats = stats
        self.estimator = Estimator(self.estimation_state, self.stats)
        self.oom_handler = OOMHandler()
        self.oom_handler_client = OOMHandlerClient(self.oom_handler, self.scheduling_state)

        self.running = False
        self.futures = {}
        self.nodes_state = {} # node to tuple(bool (schedulable or not), reason)

    def run(self, subset=None):
        self.oom_handler.start()
        self.oom_handler_client.run()
        self.scheduling_state.init_pods_work_queue(self.kube_api.load_pod_names_from_ss(subset))
        init_work_queue_size = len(self.scheduling_state.pods_work_queue)
        print(f'[Scheduler] Scheduling estimation for {init_work_queue_size} pods...')
        # TODO tqdm progress
        self.running = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=1024) as executor:
            while self.running and len(self.scheduling_state.pods_done) != init_work_queue_size:
                self.remove_done_futures()
                pod_name = self.scheduling_state.pop_or_wait_work_queue(self.futures)
                if pod_name is None:
                    self.running = False
                    break

                nodes_state = self.fetch_nodes_state()
                node_name, reason = self.get_schedulable_node(nodes_state)
                while self.running and node_name is None:
                    # we want to log only on state change
                    if self.nodes_state != nodes_state:
                        self.nodes_state = nodes_state
                        print(f'[Scheduler] No ready nodes: {nodes_state}')
                    time.sleep(1)
                    nodes_state = self.fetch_nodes_state()
                    node_name, reason = self.get_schedulable_node(nodes_state)
                self.nodes_state = nodes_state
                if not self.running:
                    break

                print(f'[Scheduler] Scheduling pod {pod_name} on node {node_name} reason {reason}')

                # these should be in scheduler thread to avoid race condition
                priority = self.scheduling_state.get_schedulable_pod_priority(node_name)
                self.scheduling_state.add_pod_to_schedule_state(pod_name, node_name, priority)

                future = executor.submit(
                    self.run_estimator,
                    pod_name=pod_name,
                    node_name=node_name,
                    priority=priority,
                )

                future.add_done_callback(functools.partial(self.done_estimation_callback, pod_name=pod_name))
                self.futures[future] = pod_name

        print('[Scheduler] Scheduler finished')

    def run_estimator(self, pod_name, node_name, priority):
        self.scheduling_state.add_phase_event(pod_name, PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED)
        payload_config = self.schedule_pod(pod_name, node_name, priority)
        reschedule, reason = False, None
        if self.running and self.scheduling_state.get_last_result_event_type(pod_name) == PodSchedulingResultEvent.POD_SCHEDULED:
            reschedule, reason = self.estimator.estimate_resources(pod_name, payload_config)
        self.delete_pod(pod_name)
        if reason is None:
            reason = self.scheduling_state.get_last_result_event_type(pod_name)

        return reschedule, reason

    def schedule_pod(self, pod_name, node_name, priority):
        payload_config = None
        try:
            cm_name = cm_name_pod_name(pod_name)
            payload_config, _ = self.kube_api.get_payload(cm_name)
            self.kube_api.create_raw_pod(pod_name, node_name, priority)

        except kubernetes.client.exceptions.ApiException as e:
            if json.loads(e.body)['reason'] == 'AlreadyExists':
                result = PodSchedulingResultEvent.INTERRUPTED_POD_ALREADY_EXISTS
                self.scheduling_state.add_result_event(pod_name, result)
                return payload_config
            else:
                # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
                raise e
        except Exception as e:
            # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
            self.scheduling_state.add_result_event(pod_name, PodSchedulingResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e  # TODO should raise?

        if not self.running:
            # do not wait for confirm when exiting:
            return

        timed_out = not self.scheduling_state.wait_event(pod_name, SchedulingTimeouts.POD_SCHEDULED_TIMEOUT)
        if timed_out:
            self.scheduling_state.add_result_event(pod_name, PodSchedulingResultEvent.INTERRUPTED_TIMEOUT)
        else:
            self.scheduling_state.add_result_event(pod_name, PodSchedulingResultEvent.POD_SCHEDULED)

        return payload_config

    def delete_pod(self, pod_name):
        self.scheduling_state.add_phase_event(pod_name, PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED)
        try:
            self.kube_api.delete_raw_pod(pod_name)
        except kubernetes.client.exceptions.ApiException as e:
            if json.loads(e.body)['reason'] == 'NotFound':
                result = PodSchedulingResultEvent.INTERRUPTED_POD_NOT_FOUND
                self.scheduling_state.add_result_event(pod_name, result)
                return
            else:
                # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
                raise e
        except Exception as e:
            # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
            self.scheduling_state.add_result_event(pod_name, PodSchedulingResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e  # TODO should raise?

        if not self.running:
            # do not wait for confirm when exiting:
            return

        timed_out = not self.scheduling_state.wait_event(pod_name, SchedulingTimeouts.POD_DELETED_TIMEOUT)
        if timed_out:
            self.scheduling_state.add_result_event(pod_name, PodSchedulingResultEvent.INTERRUPTED_TIMEOUT)
        else:
            self.scheduling_state.add_result_event(pod_name, PodSchedulingResultEvent.POD_DELETED)

    def remove_done_futures(self):
        for f in list(self.futures.keys()):
            if f.done():
                del self.futures[f]

    def done_estimation_callback(self, future, pod_name):
        reschedule, reason = future.result()
        self.stats.add_all_df_events(
            pod_name,
            self.kube_watcher_state,
            self.estimation_state,
            self.scheduling_state
        )
        self.stats.add_reschedules(
            pod_name,
            self.scheduling_state
        )
        self.clean_states(pod_name)
        self.scheduling_state.reschedule_or_complete(pod_name, reschedule, reason)

    def fetch_nodes_state(self):
        nodes_state = {} # node to tuple(bool (scedulable or not), reason)
        nodes = self.kube_api.get_nodes()
        success, nodes_resource_usage = self.kube_api.get_nodes_resource_usage()
        while self.running and not success:
            print(f'[Scheduler] Failed to get resource usage metrics: {nodes_resource_usage}, retrying in 10s ...')
            time.sleep(10)
            nodes = self.kube_api.get_nodes()
            success, nodes_resource_usage = self.kube_api.get_nodes_resource_usage()

        for node in nodes.items:
            node_name = node.metadata.name
            has_resource_estimator_label = False
            for label in node.metadata.labels:
                if label == 'svoe-role' and node.metadata.labels[label] == 'resource-estimator':
                    has_resource_estimator_label = True
                    break
            if not has_resource_estimator_label:
                nodes_state[node_name] = (False, NodeStateReason.NO_RESOURCE_ESTIMATOR_LABEL)
                continue

            is_ready = False
            for condition in node.status.conditions:
                if condition.type == 'Ready' and condition.status == 'True':
                    is_ready = True
                    break
            if not is_ready:
                nodes_state[node_name] = (False, NodeStateReason.NOT_READY)
                continue

            # TODO figure out heuristics to dynamically derive BULK_SCHEDULE_SIZE
            if node_name not in self.scheduling_state.pods_per_node or \
                    len(self.scheduling_state.pods_per_node[node_name]) < BULK_SCHEDULE_SIZE:
                nodes_state[node_name] = (True, NodeStateReason.SCHEDULABLE_BULK)
                continue

            last_pod = self.scheduling_state.get_last_scheduled_pod(node_name)
            # only valid case is if last pod is in active estimation phase,
            # all other phases are temporary before removal
            # also wait NODE_NEXT_SCHEDULE_PERIOD s for last pod to run successfully before scheduling more
            phase_event = self.estimation_state.get_last_phase_event(last_pod)
            if phase_event is None:
                nodes_state[node_name] = (False, NodeStateReason.LAST_POD_NOT_APPEARED)
                continue

            if phase_event.type != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                nodes_state[node_name] = (False, NodeStateReason.LAST_POD_NOT_IN_ESTIMATING_STATE)
                continue

            if int((local_now() - phase_event.local_time).total_seconds()) < NODE_NEXT_SCHEDULE_PERIOD:
                nodes_state[node_name] = (False, NodeStateReason.NOT_ENOUGH_TIME_SINCE_LAST_POD_STARTED_ESTIMATION)
                continue

            # resource mertics freshness
            if phase_event.local_time > nodes_resource_usage[node_name]['cluster_timestamp']:
                nodes_state[node_name] = (False, NodeStateReason.RESOURCES_METRICS_NOT_FRESH_SINCE_LAST_POD_STARTED_ESTIMATION)
                continue

            last_oom_time = self.scheduling_state.get_last_oom_time(node_name)
            if last_oom_time is not None and last_oom_time > nodes_resource_usage[node_name]['cluster_timestamp']:
                nodes_state[node_name] = (False, NodeStateReason.RESOURCES_METRICS_NOT_FRESH_SINCE_OOM_EVENT)
                continue

            # check resources only after freshness check
            allocatable = node.status.allocatable
            alloc_cpu = ResourceConvert.cpu(allocatable['cpu'])
            alloc_mem = ResourceConvert.memory(allocatable['memory'])

            # TODO add cpu_alloc threshold
            if (int(nodes_resource_usage[node_name]['memory']) / int(alloc_mem)) > NODE_MEMORY_ALLOC_THRESHOLD:
                nodes_state[node_name] = (False, NodeStateReason.NOT_ENOUGH_MEMORY)
                continue

            nodes_state[node_name] = (True, NodeStateReason.SCHEDULABLE_SEQUENCE)

        return nodes_state

    @staticmethod
    def get_schedulable_node(nodes_state):
        for node in nodes_state:
            if nodes_state[node][0]:
                return node, nodes_state[node][1] # reason
        return None, None

    def clean_states(self, pod_name):
        self.estimation_state.clean_wait_event(pod_name)
        self.scheduling_state.clean_wait_event(pod_name)
        self.estimation_state.clean_phase_result_events(pod_name)
        self.scheduling_state.clean_phase_result_events(pod_name)
        del self.kube_watcher_state.event_queues_per_pod[pod_name]

    def stop(self):
        print(f'[Scheduler] Stopping scheduler...')
        self.running = False
        # interrupt running tasks
        print(f'[Scheduler] Interrupting {len(self.futures)} running tasks...')
        for future in self.futures:
            pod = self.futures[future]
            self.scheduling_state.add_result_event(pod, PodSchedulingResultEvent.INTERRUPTED_STOP)
            self.scheduling_state.wake_event(pod)
            self.estimation_state.add_result_event(pod, PodEstimationResultEvent.INTERRUPTED_STOP)
            self.estimation_state.wake_event(pod)
        try:
            print(f'[Scheduler] Waiting for running tasks to finish...')
            for future in concurrent.futures.as_completed(self.futures, timeout=30):
                future.result()
            print(f'[Scheduler] Waiting for running tasks to finish done')
        except concurrent.futures._base.TimeoutError:
            print(f'[Scheduler] Waiting for running tasks to finish timeout')
        print(f'[Scheduler] Waiting for OOMHandler to terminate')
        self.oom_handler.stop()
        self.oom_handler.join()
        print(f'[Scheduler] OOMHandler terminated')
        print(f'[Scheduler] Waiting for OOMHandlerClient to terminate')
        self.oom_handler_client.stop()
        print(f'[Scheduler] OOMHandlerClient terminated')
