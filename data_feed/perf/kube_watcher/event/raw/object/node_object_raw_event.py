from perf.kube_watcher.event.raw.raw_event import RawEvent


class NodeObjectRawEvent(RawEvent):
    def __init__(self, raw_event):
        super(NodeObjectRawEvent, self).__init__(raw_event)
        self.kind = raw_event['raw_object']['kind']  # Node
        self.name = raw_event['raw_object']['metadata']['name']
        self.conditions = raw_event['raw_object']['status']['conditions']

        # TODO parse this correctly
        self.phase = None if 'phase' not in raw_event['raw_object']['status'] else raw_event['raw_object']['status']['phase']