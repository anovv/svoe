import time
import datetime
import concurrent.futures
import kubernetes
import threading
import json

from perf.kube_api import KubeApi

from perf.metrics import fetch_metrics
from perf.utils import PromConnection, pod_name_from_ss, save_data
from perf.defines import CLUSTER, DATA_FEED_CONTAINER, PARALLELISM, ESTIMATION_RUN_DURATION

from perf.kube_watcher.kube_watcher import KubeWatcher, CHANNEL_DF_POD_KUBE_EVENTS, CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS, CHANNEL_NODE_OBJECT_EVENTS
from perf.kube_watcher.event.logged.kube_event.pod_kube_events_log import PodKubeLoggedEvent
from perf.kube_watcher.event.logged.object.pod_object_events_log import PodObjectLoggedEvent
from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent
from perf.scheduler.scheduler import Scheduler


class PodEstimationStateEvent(PodLoggedEvent):
    # TODO ss not found, ss already running, etc.
    WAITING_FOR_POD_TO_BE_SCHEDULED = 'PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_SCHEDULED'
    WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE = 'PodEstimationStateEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE'
    WAITING_FOR_POD_TO_START_ESTIMATION_RUN = 'PodEstimationStateEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN'
    WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN = 'PodEstimationStateEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN'
    COLLECTING_METRICS = 'PodEstimationStateEvent.COLLECTING_METRICS'
    WAITING_FOR_POD_TO_BE_DELETED = 'PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_DELETED'


class PodEstimationResultEvent(PodEstimationStateEvent):
    POD_SCHEDULED = 'PodEstimationResultEvent.POD_SCHEDULED'
    DF_CONTAINER_IMAGE_PULLED = 'PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED'
    POD_STARTED_ESTIMATION_RUN = 'PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN'
    POD_FINISHED_ESTIMATION_RUN = 'PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN'
    METRICS_COLLECTED_MISSING = 'PodEstimationResultEvent.METRICS_COLLECTED_MISSING'
    METRICS_COLLECTED_ALL = 'PodEstimationResultEvent.METRICS_COLLECTED_ALL'
    POD_DELETED = 'PodEstimationResultEvent.POD_DELETED'

    # interrupts
    INTERRUPTED_INTERNAL_ERROR = 'PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR'
    INTERRUPTED_TIMEOUT = 'PodEstimationResultEvent.INTERRUPTED_TIMEOUT'
    INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS = 'PodEstimationResultEvent.INTERRUPTED_TOO_MANY_RESTARTS'
    INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS = 'PodEstimationResultEvent.INTERRUPTED_HEALTH_LIVENESS'
    INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP = 'PodEstimationResultEvent.INTERRUPTED_HEALTH_STARTUP'
    INTERRUPTED_DF_CONTAINER_BACK_OFF = 'PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_BACK_OFF'
    INTERRUPTED_UNEXPECTED_POD_DELETION = 'PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION'

    @classmethod
    def get_interrupts(cls):
        return [
            PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR,
            PodEstimationResultEvent.INTERRUPTED_TIMEOUT,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_BACK_OFF,
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION
        ]


class Timeouts:
    POD_SCHEDULED_TIMEOUT = 2 * 60
    DF_CONTAINER_PULL_IMAGE_TIMEOUT = 20 * 60
    POD_START_ESTIMATION_RUN_TIMEOUT = 2 * 60
    POD_DELETED_TIMEOUT = 2 * 60


class ResourceEstimator:
    def __init__(self):
        self.data = {}
        self.estimation_state_events_per_pod = {}
        self.estimation_result_events_per_pod = {}
        self.wait_event_per_pod = {}
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        self.kube_api = KubeApi(core_api, apps_api)
        self.kube_watcher = KubeWatcher(core_api, [self.kube_watcher_callback])
        self.prom_connection = PromConnection()

    def estimate_resources(self, ss_name):
        pod_name = pod_name_from_ss(ss_name)
        payload_config, _ = self.kube_api.get_payload(ss_name)
        try:
            self.kube_api.set_env(ss_name, 'TESTING')
            self.kube_api.scale_up(ss_name)

            for state, result, timeout in [
                (PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_SCHEDULED, PodEstimationResultEvent.POD_SCHEDULED, Timeouts.POD_SCHEDULED_TIMEOUT),
                (PodEstimationStateEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE, PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED, Timeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
                (PodEstimationStateEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN, PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN, Timeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
                (PodEstimationStateEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN, PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN, ESTIMATION_RUN_DURATION),
            ]:
                self.set_estimation_state(pod_name, state)
                timed_out = not self.wait_event(pod_name, timeout) # blocks until callback triggers specific event

                # interrupts
                if self.get_last_estimation_result(pod_name) in PodEstimationResultEvent.get_interrupts():
                    break

                if timed_out and state != PodEstimationStateEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                    result = PodEstimationResultEvent.INTERRUPTED_TIMEOUT
                    self.add_estimation_result_event(pod_name, result)
                    break

                # successfully triggered event
                self.add_estimation_result_event(pod_name, result)

            # TODO collect metrics even on interrupts?
            if self.get_last_estimation_result(pod_name) == PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN:
                # collect metrics
                self.add_estimation_result_event(pod_name, PodEstimationStateEvent.COLLECTING_METRICS)
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

                self.add_estimation_result_event(pod_name, metrics_fetch_result)

        except Exception as e:
            self.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e # TODO should raise?
        finally:
            self.finalize(ss_name)

        return result

    def finalize(self, ss_name):
        pod_name = pod_name_from_ss(ss_name)
        self.set_estimation_state(pod_name, PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_DELETED)
        try:
            self.kube_api.scale_down(ss_name)
            self.kube_api.set_env(ss_name, '')
        except Exception as e:
            self.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e # TODO should raise?

        timed_out = not self.wait_event(pod_name, Timeouts.POD_DELETED_TIMEOUT)
        if timed_out:
            self.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_TIMEOUT)
        else:
            self.add_estimation_result_event(pod_name, PodEstimationResultEvent.POD_DELETED)

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
            self.kube_watcher.stop([CHANNEL_NODE_OBJECT_EVENTS, CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS, CHANNEL_DF_POD_KUBE_EVENTS])
            self.kube_watcher = None

    def kube_watcher_callback(self, event):
        print(event)

    def _kube_watcher_callback(self, event):
        pod_name = event.pod_name
        container_name = event.container_name
        if self.get_last_estimation_state(pod_name) != PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.get_last_estimation_result(pod_name) \
                    in [*PodEstimationResultEvent.get_interrupts(), PodEstimationResultEvent.POD_DELETED]:

            # If interrupted we skip everything except pod deletion event
            print(f'skipped {event.data}')
            return

        if self.get_last_estimation_state(pod_name) == PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_SCHEDULED \
                and event.type == PodKubeLoggedEvent.POD_EVENT \
                and event.data['reason'] == 'Scheduled':
            self.wake_event(pod_name)
            return

        if self.get_last_estimation_state(pod_name) == PodEstimationStateEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE \
                and event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'Pulled':
            self.wake_event(pod_name)
            return

        # TODO wait for containers to started/ready==True?
        if self.get_last_estimation_state(pod_name) == PodEstimationStateEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN \
                and event.type == PodObjectLoggedEvent.CONTAINER_STATE_CHANGED:

            all_containers_running = False
            if 'containerStatuses' in event.raw_event.status:
                all_containers_running = True
                for container_status in event.raw_event.status['containerStatuses']:
                    if 'running' not in container_status['state']:
                        all_containers_running = False

            if all_containers_running:
                self.wake_event(pod_name)
                return

        if self.get_last_estimation_state(pod_name) == PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and event.type == PodObjectLoggedEvent.POD_DELETED:
            self.wake_event(pod_name)
            return

        # Interrupts
        # data-feed-container Back off # TODO should this be only for data-feed-container ?
        if event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'BackOff':

            self.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_BACK_OFF)
            self.wake_event(pod_name)
            return

        # Unexpected pod deletion
        if event.type == PodObjectLoggedEvent.POD_DELETED \
                and self.get_last_estimation_state(pod_name) != PodEstimationStateEvent.WAITING_FOR_POD_TO_BE_DELETED:

            self.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION)
            self.wake_event(pod_name)
            return

        # data-feed-container Restarts
        if event.type == PodObjectLoggedEvent.CONTAINER_RESTART_COUNT_CHANGED \
                and container_name == DATA_FEED_CONTAINER\
                and 'containerStatuses' in event.data:

            for cs in event.data['containerStatuses']:
                if cs['name'] == DATA_FEED_CONTAINER and int(cs['restartCount']) >= 3:
                    self.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS)
                    self.wake_event(pod_name)
                    return

        # data-feed-container Unhealthy(Liveness or Startup):
        if event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and (event.data['reason'] == 'UnhealthyLiveness' or event.data['reason'] == 'UnhealthyStartup'):

            if self.kube_watcher.pod_kube_events_log.get_unhealthy_liveness_count(pod_name, container_name) >= 5:
                # TODO check number in a timeframe instead of total
                self.add_estimation_result_event(pod_name,
                                                 PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS)
                self.wake_event(pod_name)
                return

            if self.kube_watcher.pod_kube_events_log.get_unhealthy_startup_count(pod_name, container_name) >= 10:
                # TODO check number in a timeframe instead of total
                self.add_estimation_result_event(pod_name,
                                                 PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP)
                self.wake_event(pod_name)
                return

        # TODO 'reason': 'NodeNotReady'
        # TODO watch for PodKubeLoggedEvent.CONTAINER_EVENT, {'reason': 'Failed', 'count': 2, 'message': 'Error: ErrImagePull'}
        # TODO kube event Failed, unhealthy readiness, pod_status_phase == 'Failed', other indicators?, any other container backoff?

    def get_last_estimation_result(self, pod_name):
        if pod_name in self.estimation_result_events_per_pod:
            event = self.estimation_result_events_per_pod[pod_name][-1]
            return event.type
        return None

    def add_estimation_result_event(self, pod_name, estimation_result):
        event = PodEstimationResultEvent(
            estimation_result,
            pod_name, container_name=None,
            data=None,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=None
        )
        if pod_name in self.estimation_result_events_per_pod:
            self.estimation_result_events_per_pod[pod_name].append(event)
        else:
            self.estimation_result_events_per_pod[pod_name] = [event]
        print(event)

    def get_last_estimation_state(self, pod_name):
        if pod_name in self.estimation_state_events_per_pod:
            event = self.estimation_state_events_per_pod[pod_name][-1]
            return event.type
        return None

    def set_estimation_state(self, pod_name, estimation_state):
        event = PodEstimationStateEvent(
            estimation_state,
            pod_name, container_name=None,
            data=None,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=None
        )
        if pod_name in self.estimation_state_events_per_pod:
            self.estimation_state_events_per_pod[pod_name].append(event)
        else:
            self.estimation_state_events_per_pod[pod_name] = [event]
        print(event)

    def wake_event(self, pod_name):
        self.wait_event_per_pod[pod_name].set()
        # TODO use locks instead
        time.sleep(0.01) # to avoid race between kube watcher threads and estimator thread

    def wait_event(self, pod_name, timeout):
        # TODO check if the previous event is awaited/reset
        self.wait_event_per_pod[pod_name] = threading.Event()
        return self.wait_event_per_pod[pod_name].wait(timeout=timeout)

    def get_all_events(self, pod_name, container_name):
        events = []
        events.extend(self.kube_watcher.event_queues_per_pod[pod_name].queue)
        events.extend(self.estimation_state_events_per_pod[pod_name])
        events.extend(self.estimation_result_events_per_pod[pod_name])
        events.sort(key=lambda event: event.local_time)
        events = list(filter(lambda event: event.container_name is None or event.container_name == container_name, events))
        events = list(map(lambda event: str(event), events))
        return events

    def run(self):
        print('Started estimator')
        self.prom_connection.start()
        self.kube_watcher.start([CHANNEL_NODE_OBJECT_EVENTS, CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS, CHANNEL_DF_POD_KUBE_EVENTS])
        ss_names = self.kube_api.load_ss_names()
        # ss_names = ['data-feed-binance-spot-6d1641b134-ss', 'data-feed-binance-spot-eb540d90be-ss', 'data-feed-bybit-perpetual-cca5766921-ss']
        print(f'Scheduled estimation for {len(ss_names)} pods')
        # TODO tqdm progress
        with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLELISM) as executor:
            futures = {}
            for ss_name in ss_names:
                futures[executor.submit(self.estimate_resources, ss_name=ss_name)] = ss_name
            for future in concurrent.futures.as_completed(futures.keys()):
                res = future.result()
                print(f'Finished estimating resources for {futures[future]}: {res}')

        self.cleanup()


re = ResourceEstimator()
#
#
# @atexit.register
# def cleanup():
#     re.cleanup()

# sc = Scheduler()
# ss_names = []
# sc.run(ss_names)
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
# re.kube_api.set_env(ss_name, 'TESTING')
# print(json.dumps(re.kube_api.pod_template_from_ss('data-feed-binance-spot-18257181b7-ss'), indent=4))
# re.kube_api.create_raw_pod('data-feed-binance-spot-18257181b7-ss')
re.kube_api.delete_pod('data-feed-binance-spot-18257181b7-raw')
# time.sleep(900)
# re.kube_watcher.stop()
