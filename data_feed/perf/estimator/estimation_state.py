import time
import datetime
import threading

from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent
from perf.defines import RUN_ESTIMATION_FOR


class PodEstimationPhaseEvent(PodLoggedEvent):
    # TODO ss not found, ss already running, etc.
    WAITING_FOR_POD_TO_BE_SCHEDULED = 'PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED'
    WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE = 'PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE'
    WAITING_FOR_POD_TO_START_ESTIMATION_RUN = 'PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN'
    WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN = 'PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN'
    COLLECTING_METRICS = 'PodEstimationPhaseEvent.COLLECTING_METRICS'
    WAITING_FOR_POD_TO_BE_DELETED = 'PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED'


class PodEstimationResultEvent(PodLoggedEvent):
    POD_SCHEDULED = 'PodEstimationResultEvent.POD_SCHEDULED'
    DF_CONTAINER_IMAGE_PULLED = 'PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED'
    POD_STARTED_ESTIMATION_RUN = 'PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN'
    POD_FINISHED_ESTIMATION_RUN = 'PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN'
    METRICS_COLLECTED_MISSING = 'PodEstimationResultEvent.METRICS_COLLECTED_MISSING'
    METRICS_COLLECTED_ALL = 'PodEstimationResultEvent.METRICS_COLLECTED_ALL'
    POD_DELETED = 'PodEstimationResultEvent.POD_DELETED'

    # interrupts
    INTERRUPTED_INTERNAL_ERROR = 'PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR'
    INTERRUPTED_TIMEOUT = 'PodEstimationResultEvent.INTERRUPTED_TIMEOUT'
    INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS = 'PodEstimationResultEvent.INTERRUPTED_TOO_MANY_RESTARTS'
    INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS = 'PodEstimationResultEvent.INTERRUPTED_HEALTH_LIVENESS'
    INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP = 'PodEstimationResultEvent.INTERRUPTED_HEALTH_STARTUP'
    INTERRUPTED_DF_CONTAINER_BACK_OFF = 'PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_BACK_OFF'
    INTERRUPTED_UNEXPECTED_POD_DELETION = 'PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION'

    @classmethod
    def get_interrupts(cls):
        return [
            PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR,
            PodEstimationResultEvent.INTERRUPTED_TIMEOUT,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_TOO_MANY_RESTARTS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_BACK_OFF,
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION
        ]


class Timeouts:
    POD_SCHEDULED_TIMEOUT = 2 * 60
    DF_CONTAINER_PULL_IMAGE_TIMEOUT = 20 * 60
    POD_START_ESTIMATION_RUN_TIMEOUT = 2 * 60
    POD_DELETED_TIMEOUT = 2 * 60
    POD_ESTIMATION_RUN_DURATION = RUN_ESTIMATION_FOR


class EstimationState:
    def __init__(self):
        self.estimation_phase_events_per_pod = {}
        self.estimation_result_events_per_pod = {}
        self.wait_event_per_pod = {}
        self.stats = {}

    def get_last_estimation_result(self, pod_name):
        if pod_name in self.estimation_result_events_per_pod:
            event = self.estimation_result_events_per_pod[pod_name][-1]
            return event.type
        return None

    def get_estimation_result_events(self, pod_name):
        return self.estimation_result_events_per_pod[pod_name]

    def add_estimation_result_event(self, pod_name, estimation_result):
        event = PodEstimationResultEvent(
            estimation_result,
            pod_name, container_name=None,
            data=None,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=None
        )
        if pod_name in self.estimation_result_events_per_pod:
            self.estimation_result_events_per_pod[pod_name].append(event)
        else:
            self.estimation_result_events_per_pod[pod_name] = [event]
        print(event)

    def get_last_estimation_phase(self, pod_name):
        if pod_name in self.estimation_phase_events_per_pod:
            event = self.estimation_phase_events_per_pod[pod_name][-1]
            return event.type
        return None

    def set_estimation_phase(self, pod_name, estimation_state):
        event = PodEstimationPhaseEvent(
            estimation_state,
            pod_name, container_name=None,
            data=None,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=None
        )
        if pod_name in self.estimation_phase_events_per_pod:
            self.estimation_phase_events_per_pod[pod_name].append(event)
        else:
            self.estimation_phase_events_per_pod[pod_name] = [event]
        print(event)

    def wake_event(self, pod_name):
        self.wait_event_per_pod[pod_name].set()
        # TODO use locks instead
        time.sleep(0.01) # to avoid race between kube watcher threads and estimator thread

    def wait_event(self, pod_name, timeout):
        # TODO check if the previous event is awaited/reset
        self.wait_event_per_pod[pod_name] = threading.Event()
        return self.wait_event_per_pod[pod_name].wait(timeout=timeout)

    def add_metrics_to_stats(self, pod_name, metrics):
        if pod_name not in self.stats:
            self.stats[pod_name] = {}
            self.stats[pod_name]['metrics'] = {}
        for metric_type, metric_name, metric_value, error in metrics:

            if metric_type not in self.stats[pod_name]['metrics']:
                self.stats[pod_name]['metrics'][metric_type] = {}

            # TODO somehow indicate per-metric errors?
            self.stats[pod_name]['metrics'][metric_type][metric_name] = error if error else metric_value

    def add_events_to_stats(self, pod_name, events):
        if pod_name not in self.stats:
            self.stats[pod_name] = {}
        self.stats[pod_name]['events'] = events
