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

import datetime

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


if __name__ == '__main__':
    r = Runner()
    # print(r.scheduler.oom_handler.set_oom_score_adj({'remote-scripts-ds-q26fc': {'remote-scripts-runner': '-1000'}}, 'minikube-1-m03'))
    # print(r.scheduler.oom_handler.get_oom_score({'remote-scripts-ds-q26fc': {'remote-scripts-runner': None}}, 'minikube-1-m03'))
    # print(r.scheduler.oom_handler._get_remote_scripts_pod('minikube-1-m03'))
    # r.scheduler.oom_handler.try_get_pids_and_set_oom_score_adj('data-feed-binance-spot-6d1641b134')
    # time.sleep(60)
    # @atexit.register
    # def cleanup():
    #     r.cleanup()

    # subset = ['data-feed-binance-spot-6d1641b134-ss', 'data-feed-binance-spot-eb540d90be-ss', 'data-feed-bybit-perpetual-cca5766921-ss']
    sub = [
        'data-feed-binance-spot-6d1641b134-ss',
        'data-feed-binance-spot-eb540d90be-ss',
        'data-feed-binance-spot-18257181b7-ss',
        'data-feed-binance-spot-28150ca2ec-ss',
        'data-feed-binance-spot-2d2a017a56-ss',
        'data-feed-binance-spot-3dd6e42fd0-ss'
    ]
    r.run(sub)
    # print(r.scheduler.get_ready_node_name())

    # time.sleep(900)
    # r.kube_watcher.stop()
