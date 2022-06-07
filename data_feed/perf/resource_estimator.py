import time
import datetime
import concurrent.futures
import kubernetes
import threading
import json

from perf.kube_api import KubeApi

from perf.metrics import fetch_metrics
from perf.utils import PromConnection, save_data, ResourceConvert
from perf.defines import CLUSTER, DATA_FEED_CONTAINER, NODE_MEMORY_ALLOC_THRESHOLD, NODE_RESCHEDULE_PERIOD

from perf.kube_watcher.kube_watcher import KubeWatcher, CHANNEL_DF_POD_KUBE_EVENTS, CHANNEL_NODE_KUBE_EVENTS, \
    CHANNEL_DF_POD_OBJECT_EVENTS, CHANNEL_NODE_OBJECT_EVENTS
from perf.kube_watcher.event.logged.kube_event.pod_kube_events_log import PodKubeLoggedEvent
from perf.kube_watcher.event.logged.object.pod_object_events_log import PodObjectLoggedEvent
from perf.estimation_state import EstimationState, PodEstimationPhaseEvent, PodEstimationResultEvent, Timeouts
from perf.scheduler.scheduler import Scheduler


class ResourceEstimator:
    def __init__(self):
        self.data = {}
        self.state = EstimationState()
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        custom_objects_api = kubernetes.client.CustomObjectsApi()
        scheduling_api = kubernetes.client.SchedulingV1Api()
        self.kube_api = KubeApi(core_api, apps_api, custom_objects_api, scheduling_api)
        self.kube_watcher = KubeWatcher(core_api, [self.kube_watcher_callback])
        self.prom_connection = PromConnection()

    def estimate_resources(self, pod_name, node_name):
        payload_config, _ = self.kube_api.get_payload(pod_name)
        try:
            priority = self.state.get_schedulable_pod_priority(node_name)
            self.state.add_pod_to_schedule_state(pod_name, node_name, priority)
            self.kube_api.create_raw_pod(pod_name, node_name, priority)

            for state, result, timeout in [
                (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED, PodEstimationResultEvent.POD_SCHEDULED,
                 Timeouts.POD_SCHEDULED_TIMEOUT),
                (PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE,
                 PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED, Timeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
                (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN,
                 PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN, Timeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
                (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN,
                 PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN, Timeouts.POD_ESTIMATION_RUN_DURATION),
            ]:
                self.state.set_estimation_phase(pod_name, state)
                timed_out = not self.state.wait_event(pod_name,
                                                      timeout)  # blocks until callback triggers specific event

                # interrupts
                if self.state.get_last_estimation_result(pod_name) in PodEstimationResultEvent.get_interrupts():
                    break

                if timed_out and state != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                    # WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN timeout special case - this timeout is success
                    result = PodEstimationResultEvent.INTERRUPTED_TIMEOUT
                    self.state.add_estimation_result_event(pod_name, result)
                    break

                # successfully triggered event
                self.state.add_estimation_result_event(pod_name, result)

            # TODO collect metrics even on interrupts?
            if self.state.get_last_estimation_result(pod_name) == PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN:
                # collect metrics
                self.state.add_estimation_result_event(pod_name, PodEstimationPhaseEvent.COLLECTING_METRICS)
                metrics = fetch_metrics(pod_name, payload_config)
                metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_ALL

                # write to data
                if pod_name not in self.data:
                    self.data[pod_name] = {}
                    self.data[pod_name]['metrics'] = {}
                for metric_type, metric_name, metric_value, error in metrics:
                    if error:
                        metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_MISSING

                    if metric_type not in self.data[pod_name]['metrics']:
                        self.data[pod_name]['metrics'][metric_type] = {}

                    # TODO somehow indicate per-metric errors?
                    self.data[pod_name]['metrics'][metric_type][metric_name] = error if error else metric_value

                self.state.add_estimation_result_event(pod_name, metrics_fetch_result)

        except Exception as e:
            self.state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e  # TODO should raise?
        finally:
            self.finalize(pod_name)

        # TODO should return whether retry estimation run or not
        return result

    def finalize(self, pod_name):
        self.state.set_estimation_phase(pod_name, PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED)
        try:
            self.kube_api.delete_raw_pod(pod_name)
        except Exception as e:
            self.state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e  # TODO should raise?

        timed_out = not self.state.wait_event(pod_name, Timeouts.POD_DELETED_TIMEOUT)
        if timed_out:
            self.state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_TIMEOUT)
        else:
            self.state.add_estimation_result_event(pod_name, PodEstimationResultEvent.POD_DELETED)
            # clean scheduling state
            self.state.remove_pod_from_schedule_state(pod_name)

        if pod_name not in self.data:
            self.data[pod_name] = {}
        self.data[pod_name]['events'] = self.get_all_events(pod_name, DATA_FEED_CONTAINER)

        # TODO clean kubewatcher api event queue/event log for this pod?
        # TODO report effective run time in case of interrupts
        # TODO report container logs

    def cleanup(self):
        # should be callable once
        save_data(self.data)
        self.data = None
        if self.prom_connection:
            self.prom_connection.stop()
            self.prom_connection = None
        if self.kube_watcher:
            self.kube_watcher.stop([CHANNEL_NODE_OBJECT_EVENTS, CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS,
                                    CHANNEL_DF_POD_KUBE_EVENTS])
            self.kube_watcher = None

    def kube_watcher_callback(self, event):
        print(event)

    def _kube_watcher_callback(self, event):
        pod_name = event.pod_name
        container_name = event.container_name
        if self.state.get_last_estimation_phase(pod_name) != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.state.get_last_estimation_result(pod_name) \
                in [*PodEstimationResultEvent.get_interrupts(), PodEstimationResultEvent.POD_DELETED]:
            # If interrupted we skip everything except pod deletion event
            print(f'skipped {event.data}')
            return

        if self.state.get_last_estimation_phase(pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED \
                and event.type == PodKubeLoggedEvent.POD_EVENT \
                and event.data['reason'] == 'Scheduled':
            self.state.wake_event(pod_name)
            return

        if self.state.get_last_estimation_phase(
                pod_name) == PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE \
                and event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'Pulled':
            self.state.wake_event(pod_name)
            return

        # TODO wait for containers to started/ready==True?
        if self.state.get_last_estimation_phase(
                pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN \
                and event.type == PodObjectLoggedEvent.CONTAINER_STATE_CHANGED:

            all_containers_running = False
            if 'containerStatuses' in event.raw_event.status:
                all_containers_running = True
                for container_status in event.raw_event.status['containerStatuses']:
                    if 'running' not in container_status['state']:
                        all_containers_running = False

            if all_containers_running:
                self.state.wake_event(pod_name)
                return

        if self.state.get_last_estimation_phase(pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and event.type == PodObjectLoggedEvent.POD_DELETED:
            self.state.wake_event(pod_name)
            return

        # Interrupts
        # data-feed-container Back off # TODO should this be only for data-feed-container ?
        if event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'BackOff':
            self.state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_BACK_OFF)
            self.state.wake_event(pod_name)
            return

        # Unexpected pod deletion
        if event.type == PodObjectLoggedEvent.POD_DELETED \
                and self.state.get_last_estimation_phase(
            pod_name) != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED:
            # TODO clean estimation/scheduling state here
            self.state.add_estimation_result_event(pod_name,
                                                   PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION)
            self.state.wake_event(pod_name)
            return

        # data-feed-container Restarts
        if event.type == PodObjectLoggedEvent.CONTAINER_RESTART_COUNT_CHANGED \
                and container_name == DATA_FEED_CONTAINER \
                and 'containerStatuses' in event.data:

            for cs in event.data['containerStatuses']:
                if cs['name'] == DATA_FEED_CONTAINER and int(cs['restartCount']) >= 3:
                    self.state.add_estimation_result_event(pod_name,
                                                           PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS)
                    self.state.wake_event(pod_name)
                    return

        # data-feed-container Unhealthy(Liveness or Startup):
        # TODO unhealthy readiness
        if event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and (event.data['reason'] == 'UnhealthyLiveness' or event.data['reason'] == 'UnhealthyStartup'):

            if self.kube_watcher.get_events_log(CHANNEL_DF_POD_KUBE_EVENTS).get_unhealthy_liveness_count(pod_name,
                                                                                                         container_name) >= 5:
                # TODO check number in a timeframe instead of total
                self.state.add_estimation_result_event(pod_name,
                                                       PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS)
                self.state.wake_event(pod_name)
                return

            if self.kube_watcher.get_events_log(CHANNEL_DF_POD_KUBE_EVENTS).get_unhealthy_startup_count(pod_name,
                                                                                                        container_name) >= 10:
                # TODO check number in a timeframe instead of total
                self.state.add_estimation_result_event(pod_name,
                                                       PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP)
                self.state.wake_event(pod_name)
                return

        # TODO 'reason': 'NodeNotReady'
        # TODO watch for PodKubeLoggedEvent.CONTAINER_EVENT, {'reason': 'Failed', 'count': 2, 'message': 'Error: ErrImagePull'}
        # TODO kube event Failed, unhealthy readiness, pod_status_phase == 'Failed', other indicators?, any other container backoff?
        # TODO OOMs
        # TODO node events

    def get_all_events(self, pod_name, container_name):
        events = []
        events.extend(self.kube_watcher.event_queues_per_pod[pod_name].queue)
        events.extend(self.state.estimation_phase_events_per_pod[pod_name])
        events.extend(self.state.estimation_result_events_per_pod[pod_name])
        events.sort(key=lambda event: event.local_time)
        events = list(
            filter(lambda event: event.container_name is None or event.container_name == container_name, events))
        events = list(map(lambda event: str(event), events))
        return events

    def run(self):
        print('Started estimator')
        self.prom_connection.start()
        self.kube_watcher.start([CHANNEL_NODE_OBJECT_EVENTS, CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS,
                                 CHANNEL_DF_POD_KUBE_EVENTS])


        # TODO these should be a part of state?
        # subset = ['data-feed-binance-spot-6d1641b134-ss', 'data-feed-binance-spot-eb540d90be-ss', 'data-feed-bybit-perpetual-cca5766921-ss']
        subset = []
        work_queue = self.kube_api.load_pod_names_from_ss(subset)
        work_queue_size = len(work_queue)
        done = []
        print(f'Scheduling estimation for {work_queue_size} pods...')
        # TODO tqdm progress
        with concurrent.futures.ThreadPoolExecutor(max_workers=256) as executor:
            futures = {}
            while len(done) != work_queue_size:
                while (node_name := self.get_ready_node_name()) is None:
                    time.sleep(1)
                pod_name = work_queue.pop()
                futures[executor.submit(self.estimate_resources, pod_name=pod_name, node_name=node_name)] = pod_name

        # TODO ideally this is not needed and should be handled as part of estimate_resources events
        # TODO should this be separated as "garbage collector" thread
        for future in concurrent.futures.as_completed(futures.keys()):
            res = future.result()
            print(f'Finished estimating resources for {futures[future]}: {res}')

        self.cleanup()

    def get_ready_node_name(self):
        nodes = self.kube_api.get_nodes()
        nodes_resource_usage = self.kube_api.get_nodes_resource_usage()
        for node in nodes['items']:
            has_resource_estimator_taint = False
            if node.spec.taints:
                for taint in node.spec.taints:
                    if taint.to_dict()['key'] == 'svoe-role' and taint.to_dict()['value'] == 'resource-estimator':
                        has_resource_estimator_taint = True
                        break
            if not has_resource_estimator_taint:
                continue

            is_ready = False
            for condition in node.conditions:
                if condition.type == 'Ready' and condition.status == 'True':
                    is_ready = True
                    break
            if not is_ready:
                continue

            allocatable = node.allocatable
            alloc_cpu = ResourceConvert.cpu(allocatable['cpu'])
            alloc_mem = ResourceConvert.cpu(allocatable['memory'])

            # TODO add cpu_alloc threshold
            if (int(nodes_resource_usage['memory']) / int(alloc_mem)) > NODE_MEMORY_ALLOC_THRESHOLD:
                continue

            # TODO figure out heuristics to dynamically derive BULK_SCHEDULE_SIZE
            BULK_SCHEDULE_SIZE = 2
            node_name = node.metadata.name
            if node_name not in self.state.pods_per_node or len(self.state.pods_per_node) <= BULK_SCHEDULE_SIZE:
                return node_name

            last_pod = self.state.get_last_scheduled_pod(node_name)
            # only valid case is if last pod is in active estimation phase,
            # all other phases are temporary before removal
            # also wait NODE_RESCHEDULE_PERIOD s for last pod to run successfully before scheduling more
            phase = self.state.get_last_estimation_phase(last_pod)
            if phase == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN \
                    and time.time() - phase.local_time.timestamp() > NODE_RESCHEDULE_PERIOD:
                return node_name

        return None


re = ResourceEstimator()
#
#
# @atexit.register
# def cleanup():
#     re.cleanup()

# s = Scheduler()
# s.get_oom_score("minikube-1-m03", "kube-proxy-fjr9n", ["kube-proxy"])
# s.set_oom_score_adj("minikube-1-m03", "kube-proxy-fjr9n", ["kube-proxy"], -1000)
# s.get_oom_score("minikube-1-m03", "kube-proxy-fjr9n", ["kube-proxy"])

# re.run()
# ss_name = 'data-feed-binance-spot-6d1641b134-ss'
# ss_name = 'data-feed-binance-spot-eb540d90be-ss'
# ss_name = 'data-feed-bybit-perpetual-cca5766921-ss'
# re.kube_watcher.running = True
# re.kube_watcher.watch_pod_kube_events()
# re.kube_watcher.start([CHANNEL_NODE_KUBE_EVENTS, CHANNEL_NODE_OBJECT_EVENTS])
# re.kube_api.create_raw_pod('data-feed-binance-spot-18257181b7-ss')
# re.kube_api.delete_pod('data-feed-binance-spot-18257181b7-raw')
# print(re.kube_api.get_nodes_resource_usage())
print(re.kube_api.get_or_create_priority_class(0))
# time.sleep(900)
# re.kube_watcher.stop()
