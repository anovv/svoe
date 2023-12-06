from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent


class NodeObjectLoggedEvent(NodeLoggedEvent):
    NODE_EVENT = 'NodeObjectLoggedEvent.NODE_EVENT'
    NODE_DELETED = 'NodeObjectLoggedEvent.NODE_DELETED'
    # TODO more types here