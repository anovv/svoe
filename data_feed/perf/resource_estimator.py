# Script to run pods (without resource spec) and record health and resource consumptions (mem/cpu)
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
    WAITING_FOR_POD_TO_START = 'WAITING_FOR_POD_TO_START'
    WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE = 'WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE'
    WAITING_FOR_POD_TO_START_ESTIMATION_RUN = 'WAITING_FOR_POD_TO_START_ESTIMATION_RUN'
    WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN = 'WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN'
    COLLECTING_METRICS = 'COLLECTING_METRICS'
    WAITING_FOR_POD_TO_BE_DESTROYED = 'WAITING_FOR_POD_TO_BE_DESTROYED'


class Timeouts:
    POD_START_TIMEOUT = 2 * 60
    DF_CONTAINER_PULL_IMAGE_TIMEOUT = 20 * 60
    POD_START_ESTIMATION_RUN_TIMEOUT = 2 * 60
    POD_DESTROYED_TIMEOUT = 2 * 60


class PodEstimationResult:
    POD_STARTED = 'POD_STARTED'
    DF_CONTAINER_IMAGE_PULLED = 'DF_CONTAINER_IMAGE_PULLED'
    POD_STARTED_ESTIMATION_RUN = 'POD_STARTED_ESTIMATION_RUN'
    POD_FINISHED_ESTIMATION_RUN = 'POD_FINISHED_ESTIMATION_RUN'
    METRICS_COLLECTED_MISSING = 'METRICS_MISSING'
    METRICS_COLLECTED_ALL = 'ALL_OK'
    POD_DESTROYED = 'POD_DESTROYED'
    INTERRUPTED = 'INTERRUPTED'
    INTERRUPTED_TIMEOUT = 'INTERRUPTED_TIMEOUT'

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
        self.estimation_state_per_pod[pod_name] = PodEstimationState.LAUNCHED_ESTIMATION
        payload_config, _ = self.kube_api.get_payload(ss_name)
        try:
            self.kube_api.set_env(ss_name, 'TESTING')
            # TODO what happens if ss already scaled to 1 (pod already running) ? abort?
            self.kube_api.scale_up(ss_name)

            # go through all awaitables first
            for state, result, timeout  in [
                (PodEstimationState.WAITING_FOR_POD_TO_START, PodEstimationResult.POD_STARTED, Timeouts.POD_START_TIMEOUT),
                (PodEstimationState.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE, PodEstimationResult.DF_CONTAINER_IMAGE_PULLED, Timeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
                (PodEstimationState.WAITING_FOR_POD_TO_START_ESTIMATION_RUN, PodEstimationResult.POD_STARTED_ESTIMATION_RUN, Timeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
                (PodEstimationState.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN, PodEstimationResult.POD_FINISHED_ESTIMATION_RUN, ESTIMATION_RUN_DURATION),
            ]:
                self.estimation_state_per_pod[pod_name] = state
                self.wait_event_per_pod[pod_name] = threading.Event()
                timed_out = self.wait_event_per_pod[pod_name].wait(timeout=timeout) # blocks until callback triggers specific event
                if timed_out:
                    result = PodEstimationResult.INTERRUPTED_TIMEOUT
                    break
                # successfully triggered event
                self.estimation_result_per_pod[pod_name] = result

            if result == PodEstimationResult.POD_FINISHED_ESTIMATION_RUN:
                # collect metrics
                metrics = fetch_metrics(pod_name, payload_config)
                self.estimation_result_per_pod[pod_name] = PodEstimationResult.METRICS_COLLECTED_ALL

                # write to data
                if pod_name not in self.data:
                    self.data[pod_name] = {}
                    self.data[pod_name]['metrics'] = {}
                for metric_type, metric_name, metric_value, error in metrics:
                    if error:
                        self.estimation_result_per_pod[pod_name] = PodEstimationResult.METRICS_COLLECTED_MISSING

                    if metric_type not in self.data[pod_name]['metrics']:
                        self.data[pod_name]['metrics'][metric_type] = {}

                    # TODO somehow indicate per-metric errors?
                    self.data[pod_name]['metrics'][metric_type][metric_name] = error if error else metric_value

        except Exception as e:
            self.estimation_result_per_pod[pod_name] = PodEstimationResult.INTERRUPTED
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
            self.estimation_result_per_pod[pod_name] = PodEstimationResult.INTERRUPTED
            raise e # TODO should raise?

        self.estimation_state_per_pod[pod_name] = PodEstimationState.WAITING_FOR_POD_TO_BE_DESTROYED
        timed_out = self.wait_event_per_pod[pod_name].wait(timeout=Timeouts.POD_DESTROYED_TIMEOUT)
        if timed_out:
            self.estimation_result_per_pod[pod_name] = PodEstimationResult.INTERRUPTED_TIMEOUT
        else:
            self.estimation_result_per_pod[pod_name] = PodEstimationResult.POD_DESTROYED

        if pod_name not in self.data:
            self.data[pod_name] = {}
        self.data[pod_name]['result'] = self.estimation_result_per_pod[pod_name]

    def run(self):
        print('Started estimator')
        self.prom_connection.start()
        # TODO start watcher here
        specs = self.kube_api.load_ss_specs()
        print(f'Scheduled estimation for {len(specs)} pods')
        # TODO tqdm progress
        with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLELISM) as executor:
            futures = {}
            for spec in specs:
                futures[executor.submit(self.estimate_resources, ss_name=spec.metadata.name)] = spec.metadata.name
            for future in concurrent.futures.as_completed(futures.keys()):
                res = future.result()
                print(f'Finished estimating resources for {futures[future]}: {res}')
        self.cleanup()

    def cleanup(self):
        # save_data(self.data) # TODO uncomment
        self.data = None
        if self.prom_connection:
            self.prom_connection.stop()
            self.prom_connection = None
        if self.kube_watcher:
            self.kube_watcher.stop()
            self.kube_watcher = None

    def kube_watcher_callback(self, event):
        pod_name = event.pod_name
        if self.estimation_result_per_pod[pod_name] in [
            PodEstimationResult.POD_DESTROYED,
            PodEstimationResult.INTERRUPTED,
            PodEstimationResult.INTERRUPTED_TIMEOUT
        ]:
            # TODO log?
            return

        if self.estimation_result_per_pod[pod_name] == PodEstimationState.WAITING_FOR_POD_TO_START:
            if event.type == PodKubeLoggedEvent.POD_EVENT:
                data = event.data
                if 'reason' in data and data['reason'] == 'Started':
                    self.wait_event_per_pod[pod_name].set()
                    time.sleep(0.1) # avoid race condition

        if self.estimation_result_per_pod[pod_name] == PodEstimationState.WAITING_FOR_POD_TO_START_ESTIMATION_RUN:
            if event.type == PodObjectLoggedEvent.POD_CONDITION_CHANGED:
                # TODO get last_raw_event and check state
                return

re = ResourceEstimator()


@atexit.register
def cleanup():
    re.cleanup()


# ss_name = 'data-feed-binance-spot-6d1641b134-ss'
# ss_name = 'data-feed-binance-spot-eb540d90be-ss'
ss_name = 'data-feed-bybit-perpetual-cca5766921-ss'
pod_name = pod_name_from_ss(ss_name)
# check_health(pod_name)
loop = asyncio.get_event_loop()
re.kube_watcher.start(loop)
re.kube_api.set_env(ss_name, 'TESTING')
loop.run_forever()
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
