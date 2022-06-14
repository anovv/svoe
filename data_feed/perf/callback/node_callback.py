
from perf.callback.callback import Callback

from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent
from perf.kube_watcher.event.logged.kube_event.node_kube_logged_event import NodeKubeLoggedEvent


class NodeCallback(Callback):

    def callback(self, event):
        if not isinstance(event, NodeLoggedEvent):
            raise ValueError(f'Unsupported event class: {event.__class__.__name__} for NodeCallback')

        if isinstance(event, NodeKubeLoggedEvent):
            # TODO debugs
            print(event)
            return