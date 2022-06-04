from perf.kube_watcher.event.logged.logged_event import LoggedEvent


class PodLoggedEvent(LoggedEvent):
    def __init__(self, type, pod_name, container_name, data, cluster_time, local_time, raw_event):
        super(PodLoggedEvent, self).__init__(type)
        self.pod_name = pod_name
        self.container_name = container_name
        self.data = data
        self.cluster_time = cluster_time
        self.local_time = local_time
        self.raw_event = raw_event

    def __str__(self):
        return f'[{self.local_time}][{self.pod_name}][{self.container_name}] {self.type}, {self.data}, {self.cluster_time}'