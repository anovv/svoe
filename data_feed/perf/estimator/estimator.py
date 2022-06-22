from perf.metrics.metrics import fetch_metrics
from perf.state.estimation_state import PodEstimationPhaseEvent, PodEstimationResultEvent, EstimationTimeouts


class Estimator:
    def __init__(self, estimation_state, stats):
        self.estimation_state = estimation_state
        self.stats = stats

    def estimate_resources(self, pod_name, payload_config):
        for state, result, timeout in [
            (PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE,
             PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED, EstimationTimeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
            (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN,
             PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN, EstimationTimeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
            (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN,
             PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN, EstimationTimeouts.POD_ESTIMATION_RUN_DURATION),
        ]:
            self.estimation_state.add_phase_event(pod_name, state)
            # blocks until callback triggers specific event
            timed_out = not self.estimation_state.wait_event(pod_name, timeout)

            # interrupts
            if self.estimation_state.is_interrupted(pod_name):
                break

            if timed_out and state != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                # WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN timeout special case - this timeout is success
                result = PodEstimationResultEvent.INTERRUPTED_TIMEOUT
                self.estimation_state.add_result_event(pod_name, result)
                break

            # successfully triggered event
            self.estimation_state.add_result_event(pod_name, result)

        # TODO collect metrics even on interrupts?
        if self.estimation_state.get_last_result_event_type(pod_name) == PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN:
            # collect metrics
            print(f'[Estimator] Fetching metrics for {pod_name}')
            self.estimation_state.add_result_event(pod_name, PodEstimationPhaseEvent.COLLECTING_METRICS)
            metrics = fetch_metrics(pod_name, payload_config)
            metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_ALL
            for _, _, _, error in metrics:
                if error:
                    metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_MISSING

            print(f'[Estimator] Done fetching metrics for {pod_name}')
            # save stats
            self.stats.add_metrics_to_stats(pod_name, metrics)
            self.estimation_state.add_result_event(pod_name, metrics_fetch_result)

        # success or not
        return self.estimation_state.has_result_type(pod_name, PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN)

        # TODO clean kubewatcher api event queue/event log for this pod?
        # TODO report effective run time in case of interrupts
        # TODO report container logs
