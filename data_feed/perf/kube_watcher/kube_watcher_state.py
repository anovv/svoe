from perf.kube_watcher.kube_watcher import CHANNEL_NODE_KUBE_EVENTS, CHANNEL_DF_POD_OBJECT_EVENTS, CHANNEL_DF_POD_KUBE_EVENTS, CHANNEL_NODE_OBJECT_EVENTS

from perf.kube_watcher.event.logged.kube_event.pod_kube_events_log import PodKubeEventsLog
from perf.kube_watcher.event.logged.kube_event.node_kube_events_log import NodeKubeEventsLog

from perf.kube_watcher.event.logged.object.pod_object_events_log import PodObjectEventsLog
from perf.kube_watcher.event.logged.object.node_object_events_log import NodeObjectEventsLog


class KubeWatcherState:
    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.event_queues_per_pod = {}
        self.event_queues_per_node = {}
        self.event_logs_per_channel = {}

        # init event logs per channel
        for channel, events_log in [
            (CHANNEL_NODE_KUBE_EVENTS, NodeKubeEventsLog(self.event_queues_per_node, self.callbacks)),
            (CHANNEL_NODE_OBJECT_EVENTS, NodeObjectEventsLog(self.event_queues_per_node, self.callbacks)),
            (CHANNEL_DF_POD_KUBE_EVENTS, PodKubeEventsLog(self.event_queues_per_pod, self.callbacks)),
            (CHANNEL_DF_POD_OBJECT_EVENTS, PodObjectEventsLog(self.event_queues_per_pod, self.callbacks)),
        ]:
            self.event_logs_per_channel[channel] = events_log

    def get_events_log(self, channel):
        return self.event_logs_per_channel[channel]
