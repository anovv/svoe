import datetime

from perf.kube_watcher.event.raw.object.node_object_raw_event import NodeObjectRawEvent
from perf.kube_watcher.event.logged.object.node_object_logged_event import NodeObjectLoggedEvent
from perf.kube_watcher.event.logged.node_events_log import NodeEventsLog


class NodeObjectEventsLog(NodeEventsLog):

    def __init__(self, pod_event_queues, callbacks):
        super(NodeObjectEventsLog, self).__init__(pod_event_queues, callbacks)
        self.last_raw_event_per_node = {}

    def update_state(self, raw_event):
        if not isinstance(raw_event, NodeObjectRawEvent):
            raise ValueError(f'Unsupported raw_event class: {raw_event.__class__.__name__}')

        if raw_event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown raw_event.type: {raw_event.type}')

        node_name = raw_event.node_name

        if raw_event.type == 'DELETED':
            logged_event = NodeObjectLoggedEvent(
                NodeObjectLoggedEvent.NODE_DELETED,
                node_name,
                data=None,
                cluster_time=None, local_time=datetime.datetime.now(),
                raw_event=raw_event
            )
            self._log_event_and_callback(logged_event)
            self.last_raw_event_per_node[node_name] = raw_event
            return

        data = {
            'conditions': raw_event.conditions,
            # TODO phase
        }

        logged_event = NodeObjectLoggedEvent(
            NodeObjectLoggedEvent.NODE_EVENT,
            node_name,
            data=data,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=raw_event
        )
        self._log_event_and_callback(logged_event)
        self.last_raw_event_per_node[node_name] = raw_event
