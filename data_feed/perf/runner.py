import kubernetes

from perf.defines import CLUSTER
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


class Runner:
    def __init__(self):
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        custom_objects_api = kubernetes.client.CustomObjectsApi()
        scheduling_api = kubernetes.client.SchedulingV1Api()
        self.kube_api = KubeApi(core_api, apps_api, custom_objects_api, scheduling_api)

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

        self.kube_watcher = KubeWatcher(core_api, self.kube_watcher_state)
        self.prom_connection = PromConnection()

    def run(self, subset=None):
        print('Started estimator')
        # self.prom_connection.start() # TODO
        self.kube_watcher.start([
            CHANNEL_NODE_OBJECT_EVENTS,
            CHANNEL_NODE_KUBE_EVENTS,
            CHANNEL_DF_POD_OBJECT_EVENTS,
            CHANNEL_DF_POD_KUBE_EVENTS])
        self.scheduler.run(subset)

    def cleanup(self):
        # should be callable once
        self.stats.save()
        if self.prom_connection:
            self.prom_connection.stop()
            self.prom_connection = None
        if self.kube_watcher:
            self.kube_watcher.stop([
                CHANNEL_NODE_OBJECT_EVENTS,
                CHANNEL_NODE_KUBE_EVENTS,
                CHANNEL_DF_POD_OBJECT_EVENTS,
                CHANNEL_DF_POD_KUBE_EVENTS])
            self.kube_watcher = None


r = Runner()
print(r.scheduler.oom_handler.set_oom_score_adj({'remote-scripts-ds-q26fc': {'remote-scripts-runner': '-1000'}}, 'minikube-1-m03'))
# print(r.scheduler.oom_handler.get_oom_score({'remote-scripts-ds-q26fc': {'remote-scripts-runner': None}}, 'minikube-1-m03'))
# print(r.scheduler.oom_handler._get_remote_scripts_pod('minikube-1-m03'))
# @atexit.register
# def cleanup():
#     r.cleanup()

# subset = ['data-feed-binance-spot-6d1641b134-ss', 'data-feed-binance-spot-eb540d90be-ss', 'data-feed-bybit-perpetual-cca5766921-ss']
sub = ['data-feed-binance-spot-6d1641b134-ss',
       'data-feed-binance-spot-eb540d90be-ss']
       # 'data-feed-binance-spot-18257181b7-ss',
       # 'data-feed-binance-spot-28150ca2ec-ss',
       # 'data-feed-binance-spot-2d2a017a56-ss',
       # 'data-feed-binance-spot-3dd6e42fd0-ss',]
# r.run(sub)
# ss_name = 'data-feed-binance-spot-6d1641b134-ss'
# ss_name = 'data-feed-binance-spot-eb540d90be-ss'
# ss_name = 'data-feed-bybit-perpetual-cca5766921-ss'
# r.kube_watcher.running = True
# r.kube_watcher.watch_pod_kube_events()
# r.kube_watcher.start([CHANNEL_DF_POD_OBJECT_EVENTS])
# r.kube_api.create_raw_pod('data-feed-binance-spot-18257181b7-ss')
# r.kube_api.delete_pod('data-feed-binance-spot-18257181b7-raw')
# print(r.kube_api.get_nodes_resource_usage())
# print(r.scheduler.get_ready_node_name())

# time.sleep(900)
# r.kube_watcher.stop()
