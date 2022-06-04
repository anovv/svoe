from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent


class NodeKubeLoggedEvent(NodeLoggedEvent):
    NODE_EVENT = 'NodeKubeLoggedEvent.NODE_EVENT'
    # TODO more types here