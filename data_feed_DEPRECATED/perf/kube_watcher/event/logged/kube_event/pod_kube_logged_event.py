from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent


class PodKubeLoggedEvent(PodLoggedEvent):
    # this class corresponds to kube apis v1.Event object changes, sourced from list_event_for_all_namespaces
    POD_EVENT = 'PodKubeLoggedEvent.POD_EVENT'
    CONTAINER_EVENT = 'PodKubeLoggedEvent.CONTAINER_EVENT'