# TODO break down into separate scenario specific callbacks
from perf.defines import DATA_FEED_CONTAINER

from perf.kube_watcher.event.logged.node_logged_event import NodeLoggedEvent
from perf.kube_watcher.event.logged.kube_event.node_kube_logged_event import NodeKubeLoggedEvent

from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent
from perf.kube_watcher.event.logged.kube_event.pod_kube_events_log import PodKubeLoggedEvent
from perf.kube_watcher.event.logged.object.pod_object_events_log import PodObjectLoggedEvent

from perf.estimator.estimation_state import PodEstimationPhaseEvent, PodEstimationResultEvent


class PodCallback:
    def __init__(self, estimation_state):
        self.estimation_state = estimation_state

    # def _callback(self, event):
    #     print(event)

    def callback(self, event):
        if not isinstance(event, PodLoggedEvent):
            # TODO raise if wrong event type
            return

        # TODO ignore events if estimation has not started?

        pod_name = event.pod_name
        container_name = event.container_name

        if self.estimation_state.get_last_estimation_phase_event_type(pod_name) != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.estimation_state.get_last_estimation_result_event_type(pod_name) \
                in [*PodEstimationResultEvent.get_interrupts(), PodEstimationResultEvent.POD_DELETED]:
            # If interrupted we skip everything except pod deletion event
            # TODO debug
            # print(f'skipped {event.data}')
            return

        if self.estimation_state.get_last_estimation_phase_event_type(pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED \
                and event.type == PodKubeLoggedEvent.POD_EVENT \
                and event.data['reason'] == 'Scheduled':
            self.estimation_state.wake_event(pod_name)
            return

        if self.estimation_state.get_last_estimation_phase_event_type(
                pod_name) == PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE \
                and event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'Pulled':
            self.estimation_state.wake_event(pod_name)
            return

        # TODO wait for containers to started/ready==True?
        if self.estimation_state.get_last_estimation_phase_event_type(
                pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN \
                and event.type == PodObjectLoggedEvent.CONTAINER_STATE_CHANGED:

            all_containers_running = False
            if 'containerStatuses' in event.raw_event.status:
                all_containers_running = True
                for container_status in event.raw_event.status['containerStatuses']:
                    if 'running' not in container_status['state']:
                        all_containers_running = False
            # TODO running is not sufficient
            if all_containers_running:
                self.estimation_state.wake_event(pod_name)
                return

        if self.estimation_state.get_last_estimation_phase_event_type(pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and event.type == PodObjectLoggedEvent.POD_DELETED:
            self.estimation_state.wake_event(pod_name)
            return

        # Interrupts
        # Unexpected container termination
        if event.type == PodObjectLoggedEvent.CONTAINER_STATE_CHANGED \
                and 'terminated' in event.data['state'] \
                and self.estimation_state.get_last_estimation_phase_event_type(pod_name) != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.estimation_state.has_estimation_result_type(pod_name, PodEstimationResultEvent.POD_SCHEDULED):
            self.estimation_state.add_estimation_result_event(pod_name,
                                                              PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION)
            self.estimation_state.wake_event(pod_name)

        # Unexpected pod deletion
        if event.type == PodObjectLoggedEvent.POD_DELETED \
                and self.estimation_state.get_last_estimation_phase_event_type(pod_name) != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.estimation_state.has_estimation_result_type(pod_name, PodEstimationResultEvent.POD_SCHEDULED):

            self.estimation_state.add_estimation_result_event(pod_name,
                                                              PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION)
            self.estimation_state.wake_event(pod_name)
            return

        # data-feed-container Unhealthy(Liveness or Startup):
        # TODO unhealthy readiness
        if event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and (event.data['reason'] == 'UnhealthyLiveness' or event.data['reason'] == 'UnhealthyStartup'):

            if event.data['count'] >= 5:
                # TODO check number in a timeframe instead of total
                self.estimation_state.add_estimation_result_event(pod_name,
                                                                  PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS)
                self.estimation_state.wake_event(pod_name)
                return

            if event.data['count'] >= 10:
                # TODO check number in a timeframe instead of total
                self.estimation_state.add_estimation_result_event(pod_name,
                                                                  PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP)
                self.estimation_state.wake_event(pod_name)
                return

        # TODO 'reason': 'NodeNotReady'
        # TODO watch for PodKubeLoggedEvent.CONTAINER_EVENT, {'reason': 'Failed', 'count': 2, 'message': 'Error: ErrImagePull'}
        # TODO kube event Failed, unhealthy readiness, pod_status_phase == 'Failed', other indicators?, any other container backoff?
        # TODO OOMs
        # TODO node events


class NodeCallback:
    def __init__(self, scheduling_state):
        self.scheduling_state = scheduling_state

    def callback(self, event):
        if not isinstance(event, NodeLoggedEvent):
            # TODO raise if wrong event type
            return

        if isinstance(event, NodeKubeLoggedEvent):
            # TODO debugs
            print(event)
            return

