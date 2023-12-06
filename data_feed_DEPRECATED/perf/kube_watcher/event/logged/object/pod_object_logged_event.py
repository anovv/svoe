from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent


class PodObjectLoggedEvent(PodLoggedEvent):
    # this class corresponds to kube apis v1.Pod object changes, sourced from list_pod_for_all_namespaces
    POD_DELETED = 'PodObjectLoggedEvent.POD_DELETED'
    POD_PHASE_CHANGED = 'PodObjectLoggedEvent.POD_PHASE_CHANGED'
    POD_CONDITION_CHANGED = 'PodObjectLoggedEvent.POD_CONDITION_CHANGED'
    CONTAINER_STATE_CHANGED = 'PodObjectLoggedEvent.CONTAINER_STATE_CHANGED'
    CONTAINER_STARTUP_PROBE_STATE_CHANGED = 'PodObjectLoggedEvent.CONTAINER_STARTUP_PROBE_STATE_CHANGED'
    CONTAINER_READINESS_PROBE_STATE_CHANGED = 'PodObjectLoggedEvent.CONTAINER_READINESS_PROBE_STATE_CHANGED'
    CONTAINER_RESTART_COUNT_CHANGED = 'PodObjectLoggedEvent.CONTAINER_RESTART_COUNT_CHANGED'