
from perf.state.phase_result_state import PhaseResultState
from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent
from perf.defines import RUN_ESTIMATION_FOR


class PodEstimationPhaseEvent(PodLoggedEvent):
    WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE = 'PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE'
    WAITING_FOR_POD_TO_START_ESTIMATION_RUN = 'PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN'
    WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN = 'PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN'
    COLLECTING_METRICS = 'PodEstimationPhaseEvent.COLLECTING_METRICS'


class PodEstimationResultEvent(PodLoggedEvent):
    DF_CONTAINER_IMAGE_PULLED = 'PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED'
    POD_STARTED_ESTIMATION_RUN = 'PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN'
    POD_FINISHED_ESTIMATION_RUN = 'PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN'
    METRICS_COLLECTED_MISSING = 'PodEstimationResultEvent.METRICS_COLLECTED_MISSING'
    METRICS_COLLECTED_ALL = 'PodEstimationResultEvent.METRICS_COLLECTED_ALL'

    # interrupts
    INTERRUPTED_INTERNAL_ERROR = 'PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR'
    INTERRUPTED_TIMEOUT = 'PodEstimationResultEvent.INTERRUPTED_TIMEOUT'
    INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS = 'PodEstimationResultEvent.INTERRUPTED_HEALTH_LIVENESS'
    INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP = 'PodEstimationResultEvent.INTERRUPTED_HEALTH_STARTUP'
    INTERRUPTED_UNEXPECTED_POD_DELETION = 'PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION'
    INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION = 'PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION'


class EstimationTimeouts:
    DF_CONTAINER_PULL_IMAGE_TIMEOUT = 20 * 60
    POD_START_ESTIMATION_RUN_TIMEOUT = 2 * 60
    POD_ESTIMATION_RUN_DURATION = RUN_ESTIMATION_FOR


class EstimationState(PhaseResultState):
    def __init__(self):
        super(EstimationState, self).__init__()

    def get_interrupts(self):
        return [
            PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR,
            PodEstimationResultEvent.INTERRUPTED_TIMEOUT,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP,
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION,
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION,
        ]
