import time
import concurrent.futures
import functools
import kubernetes
import json

from perf.defines import NODE_NEXT_SCHEDULE_PERIOD
from perf.estimator.estimator import Estimator
from perf.state.phase_result_scheduling_state import PodSchedulingResultEvent, PodSchedulingPhaseEvent, SchedulingTimeouts
from perf.state.estimation_state import PodEstimationPhaseEvent
from perf.kube_api.resource_convert import ResourceConvert
from perf.scheduler.oom.oom_handler import OOMHandler

class Scheduler:
    def __init__(self, kube_api, scheduling_state, estimation_state, kube_watcher_state, stats):
        self.kube_api = kube_api
        self.scheduling_state = scheduling_state
        self.estimation_state = estimation_state
        self.kube_watcher_state = kube_watcher_state

        self.stats = stats
        self.estimator = Estimator(self.estimation_state, self.stats)
        self.oom_handler = OOMHandler(self.scheduling_state)

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

                node_name, reason, node_state = self.get_ready_node_name()
                while node_name is None and self.running:
                    # print(f'No ready nodes: {node_state}')
                    time.sleep(1)
                    node_name, reason, node_state = self.get_ready_node_name()

                print(f'Scheduling pod {pod_name} on node {node_name} reason {reason}')

                future = executor.submit(
                    self.run_estimator,
                    pod_name=pod_name,
                    node_name=node_name,
                )

                future.add_done_callback(functools.partial(self.done_estimation_callback, pod_name=pod_name))
                self.futures[future] = pod_name

        print('Scheduler finished')

    def run_estimator(self, pod_name, node_name):
        priority = self.scheduling_state.get_schedulable_pod_priority(node_name)
        self.scheduling_state.add_pod_to_schedule_state(pod_name, node_name, priority)
        self.scheduling_state.add_phase_event(pod_name, PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED)
        payload_config = self.schedule_pod(pod_name, node_name, priority)
        if self.scheduling_state.get_last_result_event_type(pod_name) == PodSchedulingResultEvent.POD_SCHEDULED:
            self.estimator.estimate_resources(pod_name, payload_config)
        self.delete_pod(pod_name)

    def schedule_pod(self, pod_name, node_name, priority):
        payload_config = None
        try:
            payload_config, _ = self.kube_api.get_payload(pod_name)
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
        print(f'Done {pod_name}')
        success = future.result()
        self.scheduling_state.reschedule_or_complete(pod_name, success)
        if success:
            # TODO add reschedule event ?
            self.stats.add_all_df_events_to_stats(
                pod_name,
                self.estimation_state,
                self.scheduling_state,
                self.kube_watcher_state
            )
        self.clean_states(pod_name)

    def get_ready_node_name(self):
        # TODO enum for reasons
        # TODO move state to watcher
        # TODO move this logic to watcher and use callbacks
        nodes_state = {}

        nodes = self.kube_api.get_nodes()
        # TODO metrics-server updates info every 15s
        # make sure we wait here for updated info?
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
                nodes_state[node_name] = 'NO_RE_TAINT'
                continue

            is_ready = False
            for condition in node.status.conditions:
                if condition.type == 'Ready' and condition.status == 'True':
                    is_ready = True
                    break
            if not is_ready:
                nodes_state[node_name] = 'NO_NOT_READY'
                continue

            allocatable = node.status.allocatable
            alloc_cpu = ResourceConvert.cpu(allocatable['cpu'])
            alloc_mem = ResourceConvert.memory(allocatable['memory'])

            # TODO add cpu_alloc threshold
            # TODO restore this after debug
            # if (int(nodes_resource_usage[node_name]['memory']) / int(alloc_mem)) > NODE_MEMORY_ALLOC_THRESHOLD:
            #     continue

            # TODO figure out heuristics to dynamically derive BULK_SCHEDULE_SIZE
            BULK_SCHEDULE_SIZE = 2
            if node_name not in self.scheduling_state.pods_per_node or len(self.scheduling_state.pods_per_node[node_name]) < BULK_SCHEDULE_SIZE:
                nodes_state[node_name] = 'OK'
                return node_name, 'BULK_SCHEDULE', nodes_state

            last_pod = self.scheduling_state.get_last_scheduled_pod(node_name)
            # only valid case is if last pod is in active estimation phase,
            # all other phases are temporary before removal
            # also wait NODE_NEXT_SCHEDULE_PERIOD s for last pod to run successfully before scheduling more
            phase_event = self.estimation_state.get_last_phase_event(last_pod)
            if phase_event is None:
                nodes_state[node_name] = 'NO_LAST_EVENT'
                continue
            if phase_event.type != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                nodes_state[node_name] = 'LAST_POD_NOT_IN_WAITING_STATE'
                continue

            if time.time() - phase_event.local_time.timestamp() > NODE_NEXT_SCHEDULE_PERIOD:
                nodes_state[node_name] = 'OK'
                return node_name, 'NEXT_SCHEDULE', nodes_state
            else:
                nodes_state[node_name] = f'WAITING_FOR_NEXT({time.time() - phase_event.local_time.timestamp()})'

        return None, 'NO_SCHEDULABLE_NODES', nodes_state

    def clean_states(self, pod_name):
        self.estimation_state.clean_phase_result_events(pod_name)
        self.scheduling_state.clean_phase_result_events(pod_name)
        del self.kube_watcher_state.event_queues_per_pod[pod_name]

    def stop(self):
        return  # TODO
