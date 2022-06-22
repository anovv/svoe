from perf.callback.callback import Callback

from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent
from perf.kube_watcher.event.logged.kube_event.node_kube_logged_event import NodeKubeLoggedEvent
from perf.state.estimation_state import PodEstimationResultEvent


class NodeCallback(Callback):

    def callback(self, event):
        if not isinstance(event, NodeLoggedEvent):
            raise ValueError(f'Unsupported event class: {event.__class__.__name__} for NodeCallback')

        node_name = event.node_name
        if event.type == NodeKubeLoggedEvent.OOM_KILLED_PROCESS or \
                event.type == NodeKubeLoggedEvent.OOM_VICTIM_PROCESS:
            pid = event.data['pid']
            pod, container = self.scheduling_state.find_pod_container_by_pid(pid)
            self.scheduling_state.mark_last_oom_time(node_name)
            if pod is None:
                # pid not found, pod should be handled by liveness probe
                print(f'[OOM NodeEvent][{node_name}] Found no pod with pid {pid}, defering to liveness cleanup...')
            else:
                if not self.estimation_state.is_interrupted(pod):
                    self.estimation_state.add_result_event(pod, PodEstimationResultEvent.INTERRUPTED_OOM)
                    self.estimation_state.wake_event(pod)
                    marked_high = self.scheduler.oom_handler_client.last_marked_high_pod == pod
                    print(f'[OOM NodeEvent][{node_name}] Found {pod}, {"MARKED_HIGH" if marked_high else "MARKED_LOW"}, {container} by pid {pid}, interrupting...')

