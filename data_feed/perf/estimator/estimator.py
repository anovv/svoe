import kubernetes
import json

from perf.metrics.metrics import fetch_metrics
from perf.estimator.estimation_state import PodEstimationPhaseEvent, PodEstimationResultEvent, Timeouts


class Estimator:
    def __init__(self, kube_api, estimation_state):
        self.data = {}
        self.kube_api = kube_api
        self.estimation_state = estimation_state

    def estimate_resources(self, pod_name, node_name, priority):
        # TODO move to scheduler
        payload_config, _ = self.kube_api.get_payload(pod_name)
        try:
            # TODO move to scheduler
            self.kube_api.create_raw_pod(pod_name, node_name, priority)

            for state, result, timeout in [
                (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_SCHEDULED, PodEstimationResultEvent.POD_SCHEDULED,
                 Timeouts.POD_SCHEDULED_TIMEOUT),
                (PodEstimationPhaseEvent.WAITING_FOR_DF_CONTAINER_TO_PULL_IMAGE,
                 PodEstimationResultEvent.DF_CONTAINER_IMAGE_PULLED, Timeouts.DF_CONTAINER_PULL_IMAGE_TIMEOUT),
                (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_START_ESTIMATION_RUN,
                 PodEstimationResultEvent.POD_STARTED_ESTIMATION_RUN, Timeouts.POD_START_ESTIMATION_RUN_TIMEOUT),
                (PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN,
                 PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN, Timeouts.POD_ESTIMATION_RUN_DURATION),
            ]:
                self.estimation_state.add_estimation_phase_event(pod_name, state)
                timed_out = not self.estimation_state.wait_event(pod_name,
                                                                 timeout)  # blocks until callback triggers specific event

                # interrupts
                if self.estimation_state.get_last_estimation_result_event_type(pod_name) in PodEstimationResultEvent.get_interrupts():
                    break

                if timed_out and state != PodEstimationPhaseEvent.WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN:
                    # WAITING_FOR_POD_TO_FINISH_ESTIMATION_RUN timeout special case - this timeout is success
                    result = PodEstimationResultEvent.INTERRUPTED_TIMEOUT
                    self.estimation_state.add_estimation_result_event(pod_name, result)
                    break

                # successfully triggered event
                self.estimation_state.add_estimation_result_event(pod_name, result)

            # TODO collect metrics even on interrupts?
            if self.estimation_state.get_last_estimation_result_event_type(pod_name) == PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN:
                # collect metrics
                self.estimation_state.add_estimation_result_event(pod_name, PodEstimationPhaseEvent.COLLECTING_METRICS)
                metrics = fetch_metrics(pod_name, payload_config)
                metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_ALL
                for _, _, _, error in metrics:
                    if error:
                        metrics_fetch_result = PodEstimationResultEvent.METRICS_COLLECTED_MISSING

                # save stats
                self.estimation_state.add_metrics_to_stats(pod_name, metrics)
                self.estimation_state.add_estimation_result_event(pod_name, metrics_fetch_result)

        except kubernetes.client.exceptions.ApiException as e:
            if json.loads(e.body)['reason'] == 'AlreadyExists':
                result = PodEstimationResultEvent.INTERRUPTED_POD_ALREADY_EXISTS
                self.estimation_state.add_estimation_result_event(pod_name, result)
            else:
                # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
                raise e
        except Exception as e:
            # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
            self.estimation_state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e  # TODO should raise?
        finally:
            self.finalize(pod_name)

        # success or not
        return self.estimation_state.has_estimation_result_type(pod_name, PodEstimationResultEvent.POD_FINISHED_ESTIMATION_RUN)

    # TODO move to scheduler
    def finalize(self, pod_name):
        self.estimation_state.add_estimation_phase_event(pod_name, PodEstimationPhaseEvent.WAITING_FOR_POD_TO_BE_DELETED)
        try:
            self.kube_api.delete_raw_pod(pod_name)
        except kubernetes.client.exceptions.ApiException as e:
            if json.loads(e.body)['reason'] == 'NotFound':
                result = PodEstimationResultEvent.INTERRUPTED_POD_NOT_FOUND
                self.estimation_state.add_estimation_result_event(pod_name, result)
                return
            else:
                # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
                raise e
        except Exception as e:
            # TODO INTERRUPTED_INTERNAL_ERROR -> INTERRUPTED_UNKNOWN_ERROR and add exception to event
            self.estimation_state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_INTERNAL_ERROR)
            raise e  # TODO should raise?

        timed_out = not self.estimation_state.wait_event(pod_name, Timeouts.POD_DELETED_TIMEOUT)
        if timed_out:
            self.estimation_state.add_estimation_result_event(pod_name, PodEstimationResultEvent.INTERRUPTED_TIMEOUT)
        else:
            self.estimation_state.add_estimation_result_event(pod_name, PodEstimationResultEvent.POD_DELETED)

        # TODO clean kubewatcher api event queue/event log for this pod?
        # TODO report effective run time in case of interrupts
        # TODO report container logs
