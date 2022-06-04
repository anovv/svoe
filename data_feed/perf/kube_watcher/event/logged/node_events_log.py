import queue
from perf.kube_watcher.event.logged.events_log import EventsLog
from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent


class NodeEventsLog(EventsLog):
    def __init__(self, node_event_queues, callbacks):
        super(NodeEventsLog, self).__init__(callbacks)
        self.node_event_queues = node_event_queues

    def _log_event_and_callback(self, logged_event):
        if not isinstance(logged_event, NodeLoggedEvent):
            raise ValueError(f'Unsupported logged_event class: {logged_event.__class__.__name__}')
        node_name = logged_event.node_name
        if node_name not in self.node_event_queues:
            self.node_event_queues[node_name] = queue.Queue()
        q = self.node_event_queues[node_name]
        q.put(logged_event)
        for callback in self.callbacks:
            callback(logged_event)