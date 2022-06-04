from perf.kube_watcher.event.logged.logged_event import LoggedEvent


class NodeLoggedEvent(LoggedEvent):
    def __init__(self, type, node_name, data, cluster_time, local_time, raw_event):
        super(NodeLoggedEvent, self).__init__(type)
        self.node_name = node_name
        self.data = data
        self.cluster_time = cluster_time
        self.local_time = local_time
        self.raw_event = raw_event

    def __str__(self):
        return f'[{self.local_time}][{self.node_name}] {self.type}, {self.data}, {self.cluster_time}'