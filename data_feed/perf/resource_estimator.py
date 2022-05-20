# Script to run pods (without resource spec) and record health and resource consumptions (mem/cpu)
from utils import *
from metrics import *

import concurrent.futures
import atexit
import kubernetes
import kube_api
from perf.kube_watcher import kube_watcher


class ResourceEstimator:
    def __init__(self):
        self.data = {}
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        self.kube_api = kube_api.KubeApi(core_api, apps_api)
        self.kube_watcher = kube_watcher.KubeWatcher(core_api)
        self.prom_connection = PromConnection()

    def estimate_resources(self, ss_name):
        result = Result.STARTED_NOT_FINISHED
        pod_name = pod_name_from_ss(ss_name)
        payload_config, _ = self.kube_api.get_payload(ss_name)
        try:
            self.kube_api.set_env(ss_name, 'TESTING')
            # TODO what happens if ss already scaled to 1 (pod already running) ? abort?
            self.kube_api.scale_up(ss_name)
            appeared = self.kube_watcher.wait_for_pod_to(pod_name, True, 30)
            if appeared:
                running = self.kube_watcher.wait_for_pod_to_start_running(pod_name, 20 * 60)
                if running:
                    self.kube_watcher.wait_for_pod_to_run_for(pod_name, RUN_FOR_S)

                    metrics = fetch_metrics(pod_name, payload_config)
                    result = Result.ALL_OK

                    # write to data
                    if pod_name not in self.data:
                        self.data[pod_name] = {}
                        self.data[pod_name]['metrics'] = {}
                    for metric_type, metric_name, metric_value, error in metrics:
                        if error:
                            result = Result.METRICS_MISSING

                        if metric_type not in self.data[pod_name]['metrics']:
                            self.data[pod_name]['metrics'][metric_type] = {}

                        # TODO somehow indicate per-metric errors?
                        self.data[pod_name]['metrics'][metric_type][metric_name] = error if error else metric_value
                else:
                    result = Result.POD_DID_NOT_RUN
            else:
                result = Result.POD_NOT_FOUND
        except Exception as e:
            result = Result.INTERRUPTED
            raise e
        finally:
            if pod_name not in self.data:
                self.data[pod_name] = {}
            self.data[pod_name]['result'] = result
            self.finalize(ss_name)

        return result

    def finalize(self, ss_name):
        self.kube_api.scale_down(ss_name)
        self.kube_api.set_env(ss_name, '')
        self.kube_watcher.wait_for_pod_to(pod_name_from_ss(ss_name), False, 120)

    def run(self):
        print('Started estimator')
        self.prom_connection.start()
        # start watcher here
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
