from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent


class NodeKubeLoggedEvent(NodeLoggedEvent):
    NODE_EVENT = 'NodeKubeLoggedEvent.NODE_EVENT'
    OOM_VICTIM_PROCESS = 'NodeKubeLoggedEvent.OOM_VICTIM_PROCESS'
    OOM_KILLED_PROCESS = 'NodeKubeLoggedEvent.OOM_KILLED_PROCESS'