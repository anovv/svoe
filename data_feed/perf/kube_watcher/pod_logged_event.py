import queue


class PodEventsLog:
    # Base class to store logged/parsed events and trigger callbacks
    def __init__(self, pod_event_queues, callbacks):
        self.pod_event_queues = pod_event_queues
        self.callbacks = callbacks

    # Each subclass (corresponds to either PodLoggedEvent or PodKubeLoggedEvent) should implement it's own parsing logic
    def update_state(self, raw_event):
        raise ValueError('Not implemented')

    def _log_event_and_callback(self, logged_event):
        # if isinstance(logged_event, PodKubeLoggedEvent):
        #     print(logged_event)
        pod_name = logged_event.pod_name
        if pod_name not in self.pod_event_queues:
            self.pod_event_queues[pod_name] = queue.Queue()
        q = self.pod_event_queues[pod_name]
        q.put(logged_event)
        for callback in self.callbacks:
            callback(logged_event)


class PodLoggedEvent:
    # parsed event class
    def __init__(self, type, pod_name, container_name, data, cluster_time, local_time, raw_event):
        self.type = type
        self.pod_name = pod_name
        self.container_name = container_name
        self.data = data
        self.cluster_time = cluster_time
        self.local_time = local_time
        self.raw_event = raw_event

    def __str__(self):
        return f'{self.local_time}, {self.type}, {self.data}, {self.cluster_time}'


class PodKubeLoggedEvent(PodLoggedEvent):
    # this class corresponds to kube apis v1.Event object changes, sourced from list_event_for_all_namespaces
    POD_EVENT = 'PodKubeLoggedEvent.POD_EVENT'
    CONTAINER_EVENT = 'PodKubeLoggedEvent.CONTAINER_EVENT'


class PodObjectLoggedEvent(PodLoggedEvent):
    # this class corresponds to kube apis v1.Pod object changes, sourced from list_pod_for_all_namespaces
    POD_DELETED = 'PodObjectLoggedEvent.POD_DELETED'
    POD_PHASE_CHANGED = 'PodObjectLoggedEvent.POD_PHASE_CHANGED'
    POD_CONDITION_CHANGED = 'PodObjectLoggedEvent.POD_CONDITION_CHANGED'
    CONTAINER_STATE_CHANGED = 'PodObjectLoggedEvent.CONTAINER_STATE_CHANGED'
    CONTAINER_STARTUP_PROBE_STATE_CHANGED = 'PodObjectLoggedEvent.CONTAINER_STARTUP_PROBE_STATE_CHANGED'
    CONTAINER_READINESS_PROBE_STATE_CHANGED = 'PodObjectLoggedEvent.CONTAINER_READINESS_PROBE_STATE_CHANGED'
    CONTAINER_RESTART_COUNT_CHANGED = 'PodObjectLoggedEvent.CONTAINER_RESTART_COUNT_CHANGED'
