import functools

from perf.state.estimation_state import PodEstimationPhaseEvent, PodEstimationResultEvent, EstimationTimeouts
from perf.defines import DATA_FEED_CONTAINER, DATA_FEED_NAMESPACE


class Estimator:
    def __init__(self, kube_api, metrics_fetcher, estimation_state, stats):
        self.estimation_state = estimation_state
        self.metrics_fetcher = metrics_fetcher
        self.stats = stats
        self.kube_api = kube_api

    def estimate_resources(self, pod_name, payload_config, payload_hash):
        for phase, result, timeout in [
            (PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE,
             PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED, EstimationTimeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
            (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN,
             PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN, EstimationTimeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
            (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN,
             PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN, EstimationTimeouts.POD_ESTIMATION_RUN_DURATION),
        ]:
            self.estimation_state.add_phase_event(pod_name, phase)
            # blocks until callback triggers specific event
            timed_out = not self.estimation_state.wait_event(pod_name, timeout)
            # interrupts
            if self.estimation_state.is_interrupted(pod_name):
                break

            # TODO use self.estimation_state.get_last_phase_event_type() instead of phase here?
            if timed_out and phase != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                # WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN timeout special case - this timeout is success
                result = PodEstimationResultEvent.INTERRUPTED_TIMEOUT
                self.estimation_state.add_result_event(pod_name, result)
                break

            # successfully triggered event
            self.estimation_state.add_result_event(pod_name, result)

        # TODO collect metrics even on interrupts?
        if self.estimation_state.get_last_result_event_type(
                pod_name) == PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN:
            # collect metrics
            self.estimation_state.add_result_event(pod_name, PodEstimationPhaseEvent.COLLECTING_METRICS)

            def done_callback(future, pod_name, payload_hash, stats, estimation_state):
                metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_ALL
                metrics = future.result()
                if 'has_errors' in metrics:
                    metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_MISSING

                # save stats
                stats.add_metrics_to_stats(payload_hash, metrics)
                estimation_state.add_result_event(pod_name, metrics_fetch_result)
                print(f'[MetricsFetcher] Done fetching metrics for {pod_name}')

            self.metrics_fetcher.fetch_metrics(
                pod_name,
                payload_config,
                functools.partial(
                    done_callback,
                    pod_name=pod_name,
                    payload_hash=payload_hash,
                    stats=self.stats,
                    estimation_state=self.estimation_state
                )
            )


        # fetch df container logs
        for result_type in [
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP,
        ]:
            if self.estimation_state.has_result_type(pod_name, result_type) \
                    and self.stats.should_fetch_df_logs(pod_name, payload_config):
                logs = self.kube_api.fetch_logs(DATA_FEED_NAMESPACE, pod_name, DATA_FEED_CONTAINER)
                self.stats.add_df_logs(payload_hash, pod_name, payload_config, logs)

        # reschedule reasons
        for result_type in [
            PodEstimationResultEvent.INTERRUPTED_OOM,
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_CONTAINER_TERMINATION,
            PodEstimationResultEvent.INTERRUPTED_UNEXPECTED_POD_DELETION,
            # TODO This can be result of OOM, extra check in callback?
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_LIVENESS,
            PodEstimationResultEvent.INTERRUPTED_DF_CONTAINER_HEALTH_STARTUP,
            PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR,
        ]:
            if self.estimation_state.has_result_type(pod_name, result_type):
                return True, result_type

        return False, self.estimation_state.get_last_result_event_type(pod_name)

        # TODO report started_at, finished_at
