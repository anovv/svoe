from perf.kube_watcher.event.raw.raw_event import RawEvent


class NodeObjectRawEvent(RawEvent):
    def __init__(self, raw_event):
        super(NodeObjectRawEvent, self).__init__(raw_event)
        self.node_name = raw_event['raw_object']['metadata']['name']
        self.conditions = raw_event['raw_object']['status']['conditions']