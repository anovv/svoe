# Script to run pods (without resource spec) and record health and resource consumptions (mem/cpu)
import asyncio
import time

from utils import *
from metrics import *

import concurrent.futures
import atexit
import kubernetes
import kube_api
import threading
from perf.kube_watcher import kube_watcher
from perf.kube_watcher.pod_kube_events_log import PodKubeLoggedEvent
from perf.kube_watcher.pod_object_events_log import PodObjectLoggedEvent


class PodEstimationState:
    # TODO ss not found, ss already running, etc.
    LAUNCHED_ESTIMATION = 'LAUNCHED_ESTIMATION'
    WAITING_FOR_POD_TO_BE_SCHEDULED = 'WAITING_FOR_POD_TO_BE_SCHEDULED'
    WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE = 'WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE'
    WAITING_FOR_POD_TO_START_ESTIMATION_RUN = 'WAITING_FOR_POD_TO_START_ESTIMATION_RUN'
    WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN = 'WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN'
    COLLECTING_METRICS = 'COLLECTING_METRICS'
    WAITING_FOR_POD_TO_BE_DELETED = 'WAITING_FOR_POD_TO_BE_DELETED'


class Timeouts:
    POD_SCHEDULED_TIMEOUT = 2 * 60
    DF_CONTAINER_PULL_IMAGE_TIMEOUT = 20 * 60
    POD_START_ESTIMATION_RUN_TIMEOUT = 2 * 60
    POD_DELETED_TIMEOUT = 2 * 60


class PodEstimationResult:
    POD_SCHEDULED = 'POD_SCHEDULED'
    DF_CONTAINER_IMAGE_PULLED = 'DF_CONTAINER_IMAGE_PULLED'
    POD_STARTED_ESTIMATION_RUN = 'POD_STARTED_ESTIMATION_RUN'
    POD_FINISHED_ESTIMATION_RUN = 'POD_FINISHED_ESTIMATION_RUN'
    METRICS_COLLECTED_MISSING = 'METRICS_MISSING'
    METRICS_COLLECTED_ALL = 'ALL_OK'
    POD_DELETED = 'POD_DELETED'

    # inetrrupts
    INTERRUPTED_INTERNAL_ERROR = 'INTERRUPTED_INTERNAL_ERROR'
    INTERRUPTED_TIMEOUT = 'INTERRUPTED_TIMEOUT'
    INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS = 'INTERRUPTED_TOO_MANY_RESTARTS'
    INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS = 'INTERRUPTED_HEALTH_LIVENESS'
    INTERRUPTED_DF_CONTAINER_BACK_OFF = 'INTERRUPTED_DF_CONTAINER_BACK_OFF'
    INTERRUPTED_UNEXPECTED_POD_DELETION = 'INTERRUPTED_UNEXPECTED_POD_DELETION'

    @classmethod
    def get_interrupts(cls):
        return [
            PodEstimationResult.INTERRUPTED_INTERNAL_ERROR,
            PodEstimationResult.INTERRUPTED_TIMEOUT,
            PodEstimationResult.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS,
            PodEstimationResult.INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS,
            PodEstimationResult.INTERRUPTED_DF_CONTAINER_BACK_OFF,
            PodEstimationResult.INTERRUPTED_UNEXPECTED_POD_DELETION
        ]


class ResourceEstimator:
    def __init__(self):
        self.data = {}
        self.estimation_state_per_pod = {}
        self.estimation_result_per_pod = {}
        self.wait_event_per_pod = {}
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        self.kube_api = kube_api.KubeApi(core_api, apps_api)
        self.kube_watcher = kube_watcher.KubeWatcher(core_api, [self.kube_watcher_callback])
        self.prom_connection = PromConnection()

    def estimate_resources(self, ss_name):
        pod_name = pod_name_from_ss(ss_name)
        self.set_estimation_state(pod_name, PodEstimationState.LAUNCHED_ESTIMATION)
        payload_config, _ = self.kube_api.get_payload(ss_name)
        try:
            self.kube_api.set_env(ss_name, 'TESTING')
            # TODO what happens if ss already scaled to 1 (pod already running) ? abort?
            self.kube_api.scale_up(ss_name)

            for state, result, timeout in [
                (PodEstimationState.WAITING_FOR_POD_TO_BE_SCHEDULED, PodEstimationResult.POD_SCHEDULED, Timeouts.POD_SCHEDULED_TIMEOUT),
                (PodEstimationState.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE, PodEstimationResult.DF_CONTAINER_IMAGE_PULLED, Timeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
                (PodEstimationState.WAITING_FOR_POD_TO_START_ESTIMATION_RUN, PodEstimationResult.POD_STARTED_ESTIMATION_RUN, Timeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
                (PodEstimationState.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN, PodEstimationResult.POD_FINISHED_ESTIMATION_RUN, ESTIMATION_RUN_DURATION),
            ]:
                self.set_estimation_state(pod_name, state)
                self.wait_event_per_pod[pod_name] = threading.Event()
                timed_out = not self.wait_event_per_pod[pod_name].wait(timeout=timeout) # blocks until callback triggers specific event
                # inetrrupts
                if self.get_estimation_result(pod_name) in PodEstimationResult.get_interrupts():
                    break

                if timed_out:
                    if state == PodEstimationState.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                        result = PodEstimationResult.POD_FINISHED_ESTIMATION_RUN
                        self.set_estimation_result(pod_name, result)
                    else:
                        result = PodEstimationResult.INTERRUPTED_TIMEOUT
                        self.set_estimation_result(pod_name, result)
                        break

                # successfully triggered event
                self.set_estimation_result(pod_name, result)

            if result == PodEstimationResult.POD_FINISHED_ESTIMATION_RUN:
                # collect metrics
                metrics = fetch_metrics(pod_name, payload_config)
                self.set_estimation_result(pod_name, PodEstimationResult.METRICS_COLLECTED_ALL)

                # write to data
                if pod_name not in self.data:
                    self.data[pod_name] = {}
                    self.data[pod_name]['metrics'] = {}
                for metric_type, metric_name, metric_value, error in metrics:
                    if error:
                        self.set_estimation_result(pod_name, PodEstimationResult.METRICS_COLLECTED_MISSING)

                    if metric_type not in self.data[pod_name]['metrics']:
                        self.data[pod_name]['metrics'][metric_type] = {}

                    # TODO somehow indicate per-metric errors?
                    self.data[pod_name]['metrics'][metric_type][metric_name] = error if error else metric_value

        except Exception as e:
            self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_INTERNAL_ERROR)
            raise e # TODO should raise?
        finally:
            self.finalize(ss_name)

        return result

    def finalize(self, ss_name):
        pod_name = pod_name_from_ss(ss_name)
        try:
            self.kube_api.scale_down(ss_name)
            self.kube_api.set_env(ss_name, '')
        except Exception as e:
            self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_INTERNAL_ERROR)
            raise e # TODO should raise?

        self.set_estimation_state(pod_name, PodEstimationState.WAITING_FOR_POD_TO_BE_DELETED)
        timed_out = not self.wait_event_per_pod[pod_name].wait(timeout=Timeouts.POD_DELETED_TIMEOUT)
        if timed_out:
            self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_TIMEOUT)
        else:
            self.set_estimation_result(pod_name, PodEstimationResult.POD_DELETED)

        if pod_name not in self.data:
            self.data[pod_name] = {}
        self.data[pod_name]['result'] = self.get_estimation_result(pod_name)

        # TODO clean kubewatcher api event queue/event log for this pod?

    def cleanup(self):
        # should be callable once
        save_data(self.data)
        self.data = None
        if self.prom_connection:
            self.prom_connection.stop()
            self.prom_connection = None
        if self.kube_watcher:
            self.kube_watcher.stop()
            self.kube_watcher = None

    def kube_watcher_callback(self, event):
        pod_name = event.pod_name
        container_name = event.container_name
        if self.get_estimation_result(pod_name) \
                in [*PodEstimationResult.get_interrupts(), PodEstimationResult.POD_DELETED]:
            # TODO log?
            print(f'skipped event')
            return

        if self.get_estimation_state(pod_name) == PodEstimationState.WAITING_FOR_POD_TO_BE_SCHEDULED \
                and event.type == PodKubeLoggedEvent.POD_EVENT \
                and event.data['reason'] == 'Scheduled':
            print(f'{pod_name} scheduled')
            self.wake_event_delayed(pod_name)
            return

        # TODO Kube Event 'Pulled' doesn't show up, why? or doesn't get parse/trigerred?
        if self.get_estimation_state(pod_name) == PodEstimationState.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE \
                and event.type == PodKubeLoggedEvent.POD_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'Pulled':

            print(f'{container_name} pulled')
            self.wake_event_delayed(pod_name)
            return

        if self.get_estimation_state(pod_name) == PodEstimationState.WAITING_FOR_POD_TO_START_ESTIMATION_RUN \
                and event.type == PodObjectLoggedEvent.POD_CONDITION_CHANGED:

            last_raw_event = self.kube_watcher.pod_object_events_log.get_last_raw_event(pod_name)

            # TODO is this correct
            ready = False
            if 'conditions' in last_raw_event.status:
                ready = True
                for condition in last_raw_event.status['conditions']:
                    if condition['status'] == 'False':
                        ready = False
            if ready:
                print(f'{container_name} all conditions statuses are true')
                self.wake_event_delayed(pod_name)
                return

        if self.get_estimation_state(pod_name) == PodEstimationState.WAITING_FOR_POD_TO_BE_DELETED \
                and event.type == PodObjectLoggedEvent.POD_DELETED:

            print(f'{pod_name} deleted')
            self.wake_event_delayed(pod_name)
            return

        # Interrupts
        # Back off
        if event.type == PodKubeLoggedEvent.POD_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'BackOff':

            self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_DF_CONTAINER_BACK_OFF)
            print(f'{container_name} backoff')
            self.wake_event_delayed(pod_name)
            return

        # Unexpected pod deletion
        if event.type == PodObjectLoggedEvent.POD_DELETED \
                and self.estimation_result_per_pod[pod_name] != PodEstimationState.WAITING_FOR_POD_TO_BE_DELETED:

            self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_UNEXPECTED_POD_DELETION)
            print(f'{pod_name} unexpected delete')
            self.wake_event_delayed(pod_name)
            return

        # Restarts
        if event.type == PodObjectLoggedEvent.CONTAINER_RESTART_COUNT_CHANGED \
                and container_name == DATA_FEED_CONTAINER\
                and 'containerStatuses' in event.data:

            for cs in event.data['containerStatuses']:
                if cs['name'] == DATA_FEED_CONTAINER and int(cs['restartCount']) >= 3:
                    self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS)
                    print(f'{container_name} too many restarts')
                    self.wake_event_delayed(pod_name)
                    return

        # UnhealthyLiveness:
        if event.type == PodKubeLoggedEvent.POD_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'UnhealthyLiveness' \
                and self.kube_watcher.pod_kube_events_log.get_unhealthy_count()['Liveness'] >= 5:

            self.set_estimation_result(pod_name, PodEstimationResult.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS)
            print(f'{container_name} too many liveness probes failed')
            self.wake_event_delayed(pod_name)
            return

        # TODO unhealthy readiness, pod_status_phase == 'Failed', other indicators?

    def get_estimation_result(self, pod_name):
        if pod_name in self.estimation_result_per_pod:
            return self.estimation_result_per_pod[pod_name]
        return None

    def set_estimation_result(self, pod_name, estimation_result):
        self.estimation_result_per_pod[pod_name] = estimation_result
        print(f'Set result {estimation_result}')

    def get_estimation_state(self, pod_name):
        if pod_name in self.estimation_state_per_pod:
            return self.estimation_state_per_pod[pod_name]
        return None

    def set_estimation_state(self, pod_name, estimation_state):
        self.estimation_state_per_pod[pod_name] = estimation_state
        print(f'Set state {estimation_state}')

    def wake_event_delayed(self, pod_name):
        self.wait_event_per_pod[pod_name].set()
        # TODO this blocks event loop, fix it
        time.sleep(0.1) # avoid race conditions between kubewatcher event loop and estimation thread

    def run(self):
        print('Started estimator')
        self.prom_connection.start()
        self.kube_watcher.start()
        # ss_names = self.kube_api.load_ss_names() # TODO
        ss_names = ['data-feed-binance-spot-6d1641b134-ss']
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


@atexit.register
def cleanup():
    re.cleanup()


ss_name = 'data-feed-binance-spot-6d1641b134-ss'
# ss_name = 'data-feed-binance-spot-eb540d90be-ss'
# ss_name = 'data-feed-bybit-perpetual-cca5766921-ss'
re.kube_watcher.start()
time.sleep(2000)
# re.estimate_resources(ss_name)
# re.kube_api.set_env(ss_name, 'TESTING')
# scale_up(ss_name)
# scale_down(ss_name)
# set_env(ss_name, '')
# print(fetch_metrics(ss_name))
# loop = asyncio.get_event_loop()
# session = aiohttp.ClientSession()
# res = loop.run_until_complete(_fetch_metric_async('health', 'absent', 'avg_over_time((max(absent(svoe_data_feed_collector_conn_health_gauge{exchange="BINANCE", symbol="ETH-USDT", data_type="l2_book"})) or vector(0))[10m:])', session))
# loop.run_until_complete(session.close())
# print(res)
# launch_watch_events_thread()
# estimate_resources(ss_name)
# save_data()
# t.join()
# run_estimator()
# watch_namespaced_events()
# re.kube_watcher.watch_kube_events()
# load_ss_specs()
