import signal

from perf.kube_api.kube_api import KubeApi
from perf.kube_watcher.kube_watcher import KubeWatcher, CHANNEL_NODE_OBJECT_EVENTS, CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS, CHANNEL_DF_POD_KUBE_EVENTS
from perf.kube_watcher.kube_watcher_state import KubeWatcherState
from perf.metrics.prom_connection import PromConnection
from perf.state.estimation_state import EstimationState
from perf.scheduler.scheduler import Scheduler
from perf.state.scheduling_state import SchedulingState
from perf.callback.pod_callback import PodCallback
from perf.callback.node_callback import NodeCallback
from perf.stats.stats import Stats
from perf.defines import CLUSTER
from kube_api.utils import ss_name_from_pod_name


class Runner:
    def __init__(self, enable_oom_handler=False):
        self.kube_api = KubeApi.new_instance()
        self.scheduling_state = SchedulingState()
        self.estimation_state = EstimationState()
        self.kube_watcher_state = KubeWatcherState()
        self.stats = Stats()
        self.scheduler = Scheduler(
            self.kube_api,
            self.scheduling_state,
            self.estimation_state,
            self.kube_watcher_state,
            self.stats,
            enable_oom_handler
        )
        pod_callback = PodCallback(self.scheduler)
        node_callback = NodeCallback(self.scheduler)
        self.kube_watcher_state.register_pod_callback(pod_callback.callback)
        self.kube_watcher_state.register_node_callback(node_callback.callback)

        self.kube_watcher = KubeWatcher(self.kube_api.core_api, self.kube_watcher_state)
        self.prom_connection = PromConnection()
        self.running = False

    def run(self, subset=None, label_selector=None):
        for sig in [signal.SIGINT, signal.SIG_IGN, signal.SIGTERM]:
            signal.signal(sig, self.cleanup)
        self.running = True
        print('[Runner] Started estimator')
        if CLUSTER == 'minikube-1':
            # start prom connection only for minikube (it uses port-forwarding)
            self.prom_connection.start() # blocking
        if not self.running:
            return
        self.kube_watcher.start([
            CHANNEL_NODE_OBJECT_EVENTS,
            CHANNEL_NODE_KUBE_EVENTS,
            CHANNEL_DF_POD_OBJECT_EVENTS,
            CHANNEL_DF_POD_KUBE_EVENTS])
        self.scheduler.run
        self.cleanup()

    def rerun(self, label_selector, date):
        print(f'[Runner] Re-running {date}...')
        subset = []
        missing_metric_pods = self.missing_metric_ss(date)
        subset.extend(missing_metric_pods)
        print(f'[Runner] Re-running {len(missing_metric_pods)} pods with no metrics')
        if label_selector is not None:
            missing_queried_pods = self.missing_queried_ss(label_selector, date)
            subset.extend(missing_queried_pods)
            print(f'[Runner] Re-running {len(missing_queried_pods)} skipped queried pods')
        self.run(subset=subset)

    def missing_metric_ss(self, date):
        # pods in stats with no metrics
        res = []
        self.stats.load_date(date) # TODO fix double loading
        # rerun missing metrics
        for hash in self.stats.stats:
            item = self.stats.stats[hash]
            pod_name = item['pod_name']
            # TODO add rerun filter logic (do not rerun crashed, failed)
            if 'metrics' not in item:
                res.append(ss_name_from_pod_name(pod_name))
        return res

    def missing_queried_ss(self, label_selector, date):
        # pods queried by label_selector which did not appear in stats
        queried_pods = self.kube_api.load_pod_names_from_ss(subset=[], label_selector=label_selector)
        self.stats.load_date(date)  # TODO fix double loading
        processed_pods = []
        for hash in self.stats.stats:
            item = self.stats.stats[hash]
            pod_name = item['pod_name']
            processed_pods.append(pod_name)
        missed_pods = list(set(queried_pods) - set(processed_pods))
        missed_ss = list(map(lambda pod: ss_name_from_pod_name(pod), missed_pods))
        return missed_ss

    def cleanup(self, *args):
        # *args are for signal.signal handler
        if not self.running:
            return
        self.running = False
        if self.prom_connection is not None:
            self.prom_connection.stop()
            self.prom_connection = None
        if self.scheduler is not None:
            self.scheduler.stop()
            self.scheduler = None
        # save stats only after scheduler is done so we write all events
        self.stats.save()
        if self.kube_watcher is not None:
            self.kube_watcher.stop([
                CHANNEL_NODE_OBJECT_EVENTS,
                CHANNEL_NODE_KUBE_EVENTS,
                CHANNEL_DF_POD_OBJECT_EVENTS,
                CHANNEL_DF_POD_KUBE_EVENTS])
            self.kube_watcher = None

if __name__ == '__main__':
    r = Runner(enable_oom_handler=False)
    # TODO sort statefulsets by symbol-distribution to not have same exchange pods at the same time
    # TODO create run_info field in stats
    # TODO add label_selector to  run_info
    # r.stats.load_date('03-08-2022-16-00-45')
    label_selector = 'svoe.exchange in (PHEMEX, BINANCE, BINANCE_FUTURES),svoe.instrument-type in (spot, perpetual),svoe.symbol-distribution in (ONE_TO_ONE, LARGEST_WITH_SMALLEST, EQUAL_BUCKETS)'
    # sub = [
    #     'data-feed-binance-futures-perpetual-c0e456d94a-ss'
    # ]
    # r.run(subset=[], label_selector=label_selector)
    # r.rerun(label_selector, '03-08-2022-09-00-41')
    print(r.missing_queried_ss(label_selector, '03-08-2022-17-05-14'))
