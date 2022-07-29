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


class Runner:
    def __init__(self):
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
            self.stats
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
        self.scheduler.run(subset, label_selector)
        self.cleanup()

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
    r = Runner()
    # TODO sort statefulsets by symbol-distribution to not have same exchange pods at the same time
    label_selector = 'svoe.exchange in (PHEMEX, BINANCE, BINANCE_FUTURES),svoe.instrument-type in (spot, perpetual),svoe.symbol-distribution in (ONE_TO_ONE, LARGEST_WITH_SMALLEST, EQUAL_BUCKETS)'
    sub = [
        'data-feed-phemex-spot-0e620c0d95-ss',
        'data-feed-phemex-spot-32ee898724-ss',
        'data-feed-phemex-perpetual-078a670ba4-ss',
        'data-feed-phemex-perpetual-15811a3a1b-ss',
        'data-feed-kraken-futures-perpetual-13814beedf-ss',
        'data-feed-kraken-futures-perpetual-17b6ccc73a-ss',
        'data-feed-gateio-spot-0f6d99f340-ss',
        'data-feed-gateio-spot-1cda6d1458-ss',
        'data-feed-ftx-spot-013314981b-ss',
        'data-feed-ftx-spot-201da94f1e-ss',
        'data-feed-ftx-perpetual-096c2d8f51-ss',
        'data-feed-ftx-perpetual-0d579336c0-ss',
        'data-feed-bybit-perpetual-239b6f767f-ss',
        'data-feed-bybit-perpetual-27a48cc207-ss',
        'data-feed-binance-spot-05bbcd15c6-ss',
        'data-feed-binance-spot-0cb2ff270e-ss',
        'data-feed-binance-futures-perpetual-219409651d-ss',
        'data-feed-binance-futures-perpetual-2c070e8a30-ss',
    ]
    r.run(subset=[], label_selector=label_selector)
