
from perf.state.phase_result_state import PhaseResultState
from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent


class PodSchedulingPhaseEvent(PodLoggedEvent):
    WAITING_FOR_POD_TO_BE_SCHEDULED = 'PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED'
    WAITING_FOR_POD_TO_BE_DELETED = 'PodSchedulingPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED'


class PodSchedulingResultEvent(PodLoggedEvent):
    POD_SCHEDULED = 'PodSchedulingResultEvent.POD_SCHEDULED'
    POD_DELETED = 'PodSchedulingResultEvent.POD_DELETED'

    # interrupts
    INTERRUPTED_INTERNAL_ERROR = 'PodSchedulingResultEvent.INTERRUPTED_INTERNAL_ERROR'
    INTERRUPTED_TIMEOUT = 'PodSchedulingResultEvent.INTERRUPTED_TIMEOUT'
    INTERRUPTED_POD_ALREADY_EXISTS = 'PodEstimationResultEvent.INTERRUPTED_POD_ALREADY_EXISTS'
    INTERRUPTED_POD_NOT_FOUND = 'PodEstimationResultEvent.INTERRUPTED_POD_NOT_FOUND'


class SchedulingTimeouts:
    POD_SCHEDULED_TIMEOUT = 2 * 60
    POD_DELETED_TIMEOUT = 2 * 60


class PhaseResultSchedulingState(PhaseResultState):
    def __init__(self):
        super(PhaseResultSchedulingState, self).__init__()

    def get_interrupts(self):
        return [
            PodSchedulingResultEvent.INTERRUPTED_POD_NOT_FOUND,
            PodSchedulingResultEvent.INTERRUPTED_POD_ALREADY_EXISTS,
            PodSchedulingResultEvent.INTERRUPTED_TIMEOUT,
            PodSchedulingResultEvent.INTERRUPTED_INTERNAL_ERROR
        ]

