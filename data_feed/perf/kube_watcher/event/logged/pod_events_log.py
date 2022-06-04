import queue
from perf.kube_watcher.event.logged.events_log import EventsLog
from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent


class PodEventsLog(EventsLog):
    def __init__(self, pod_event_queues, callbacks):
        super(PodEventsLog, self).__init__(callbacks)
        self.pod_event_queues = pod_event_queues

    def _log_event_and_callback(self, logged_event):
        if not isinstance(logged_event, PodLoggedEvent):
            raise ValueError(f'Unsupported logged_event class: {logged_event.__class__.__name__}')
        pod_name = logged_event.pod_name
        if pod_name not in self.pod_event_queues:
            self.pod_event_queues[pod_name] = queue.Queue()
        q = self.pod_event_queues[pod_name]
        q.put(logged_event)
        for callback in self.callbacks:
            callback(logged_event)