
from perf.kube_watcher.event.raw.kube_event.kube_raw_event import KubeRawEvent
from perf.kube_watcher.event.logged.node_events_log import NodeEventsLog


class NodeKubeEventsLog(NodeEventsLog):
    def __init__(self, pod_event_queues, callbacks):
        super(NodeKubeEventsLog, self).__init__(pod_event_queues, callbacks)

    def update_state(self, raw_event):
        if not isinstance(raw_event, KubeRawEvent):
            raise ValueError(f'Unsupported raw_event class: {raw_event.__class__.__name__}')

        if raw_event.involved_object_kind != 'Node':
            raise ValueError(f'Unsupported involved_object_kind: {raw_event.involved_object_kind}')

        if raw_event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown raw_event.type: {raw_event.type}')

        if raw_event.object_kind != 'Event':
            raise ValueError(f'Unknown raw_event.kind: {raw_event.type}')
