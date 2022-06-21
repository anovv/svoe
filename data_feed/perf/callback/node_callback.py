from perf.callback.callback import Callback

from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent
from perf.kube_watcher.event.logged.kube_event.node_kube_logged_event import NodeKubeLoggedEvent


class NodeCallback(Callback):

    def callback(self, event):
        if not isinstance(event, NodeLoggedEvent):
            raise ValueError(f'Unsupported event class: {event.__class__.__name__} for NodeCallback')

        node_name = event.node_name
        if isinstance(event, NodeKubeLoggedEvent):
            print(event)

        if event.type == NodeKubeLoggedEvent.OOM_KILLED_PROCESS or \
                event.type == NodeKubeLoggedEvent.OOM_VICTIM_PROCESS:
            pid = event.data['pid']
            pod, container = self.scheduling_state.find_pod_container_by_pid(pid)
            # TODO check if pod was marked by OOMHandler as min?
            # TODO make sure to kill only for df pods
            self.scheduling_state.mark_last_oom_time(node_name)
            if pod is None:
                print(f'Found no pod with pid {pid}, best guess kill...')
            else:
                marked_high = self.scheduler.oom_handler_client.last_marked_high_pod == pod
                print(f'Found {pod}, {"MARKED_HIGH" if marked_high else "MARKED_LOW"}, {container} by pid {pid}, will be killed...')
