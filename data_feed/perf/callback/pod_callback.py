
from perf.callback.callback import Callback
from perf.defines import DATA_FEED_CONTAINER

from perf.state.estimation_state import PodEstimationPhaseEvent, PodEstimationResultEvent
from perf.state.phase_result_scheduling_state import PodSchedulingPhaseEvent, PodSchedulingResultEvent

from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent
from perf.kube_watcher.event.logged.kube_event.pod_kube_events_log import PodKubeLoggedEvent
from perf.kube_watcher.event.logged.object.pod_object_events_log import PodObjectLoggedEvent


class PodCallback(Callback):

    # def _callback(self, event):
    #     print(event)

    def callback(self, event):
        if not isinstance(event, PodLoggedEvent):
            raise ValueError(f'Unsupported event class: {event.__class__.__name__} for PodCallback')

        # TODO ignore events if estimation has not started?

        pod_name = event.pod_name
        container_name = event.container_name

        # Skips
        if self.scheduling_state.get_last_phase_event_type(pod_name) != PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.estimation_state.is_interrupted(pod_name):
            # If interrupted we skip everything except pod deletion event
            # TODO debug
            print(f'skipped {event.data}')
            return

        # Scheduling state
        if self.scheduling_state.get_last_phase_event_type(pod_name) == PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED \
                and event.type == PodKubeLoggedEvent.POD_EVENT \
                and event.data['reason'] == 'Scheduled':
            self.scheduling_state.wake_event(pod_name)
            return

        if self.scheduling_state.get_last_phase_event_type(pod_name) == PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and event.type == PodObjectLoggedEvent.POD_DELETED:
            self.scheduling_state.wake_event(pod_name)
            return

        if self.estimation_state.get_last_phase_event_type(
                pod_name) == PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE \
                and event.type == PodKubeLoggedEvent.CONTAINER_EVENT \
                and container_name == DATA_FEED_CONTAINER \
                and event.data['reason'] == 'Pulled':
            self.estimation_state.wake_event(pod_name)
            return

        if self.estimation_state.get_last_phase_event_type(
                pod_name) == PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN \
                and (event.type == PodObjectLoggedEvent.CONTAINER_STATE_CHANGED
                     or event.type == PodObjectLoggedEvent.CONTAINER_STARTUP_PROBE_STATE_CHANGED):

            all_containers_running = False
            all_containers_started = False
            if 'containerStatuses' in event.raw_event.status:
                all_containers_running = True
                all_containers_started = True
                for container_status in event.raw_event.status['containerStatuses']:
                    if 'running' not in container_status['state']:
                        all_containers_running = False
                    if not container_status['started']:
                        all_containers_started = False

            if all_containers_running and all_containers_started:
                self.estimation_state.wake_event(pod_name)
                self.scheduler.oom_handler_client.notify_pod_started(pod_name)
                return

        # Interrupts
        # Unexpected container termination
        if event.type == PodObjectLoggedEvent.CONTAINER_STATE_CHANGED \
                and 'terminated' in event.data['state'] \
                and self.scheduling_state.get_last_phase_event_type(pod_name) != PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.scheduling_state.has_result_type(pod_name, PodSchedulingResultEvent.POD_SCHEDULED):
            self.estimation_state.add_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION)
            self.estimation_state.wake_event(pod_name)

        # Unexpected pod deletion
        if event.type == PodObjectLoggedEvent.POD_DELETED \
                and self.scheduling_state.get_last_phase_event_type(pod_name) != PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED \
                and self.scheduling_state.has_result_type(pod_name, PodSchedulingResultEvent.POD_SCHEDULED):

            self.estimation_state.add_result_event(pod_name,
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
                self.estimation_state.add_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS)
                self.estimation_state.wake_event(pod_name)
                return

            if event.data['count'] >= 10:
                # TODO check number in a timeframe instead of total
                self.estimation_state.add_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP)
                self.estimation_state.wake_event(pod_name)
                return

        # TODO 'reason': 'NodeNotReady'
        # TODO watch for PodKubeLoggedEvent.CONTAINER_EVENT, {'reason': 'Failed', 'count': 2, 'message': 'Error: ErrImagePull'}
        # TODO kube event Failed, unhealthy readiness, pod_status_phase == 'Failed', other indicators?, any other container backoff?