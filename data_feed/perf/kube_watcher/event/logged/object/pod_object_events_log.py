import datetime
from perf.utils import equal_dicts, filtered_dict

from perf.kube_watcher.event.raw.object.pod_object_raw_event import PodObjectRawEvent
from perf.kube_watcher.event.logged.object.pod_object_logged_event import PodObjectLoggedEvent
from perf.kube_watcher.event.logged.pod_events_log import PodEventsLog


class PodObjectEventsLog(PodEventsLog):

    def __init__(self, pod_event_queues, callbacks):
        super(PodObjectEventsLog, self).__init__(pod_event_queues, callbacks)
        # v1 Pod object change event contains info about both pod and container specific events,
        # hence no separation per type event type, only per pod
        self.last_raw_event_per_pod = {}

    def update_state(self, raw_event):
        if not isinstance(raw_event, PodObjectRawEvent):
            raise ValueError(f'Unsupported raw_event class: {raw_event.__class__.__name__}')

        if raw_event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown raw_event.type: {raw_event.type}')

        pod_name = raw_event.pod_name

        if raw_event.type == 'DELETED':
            logged_event = PodObjectLoggedEvent(
                PodObjectLoggedEvent.POD_DELETED,
                pod_name, container_name=None,
                data=None,
                cluster_time=None, local_time=datetime.datetime.now(),
                raw_event=raw_event
            )
            self._log_event_and_callback(logged_event)
            self.last_raw_event_per_pod[pod_name] = raw_event
            return

        # phase change
        if 'phase' in raw_event.status:
            if pod_name not in self.last_raw_event_per_pod \
                    or 'phase' not in self.last_raw_event_per_pod[pod_name].status \
                    or self.last_raw_event_per_pod[pod_name].status['phase'] != raw_event.status['phase']:
                logged_event = PodObjectLoggedEvent(
                    PodObjectLoggedEvent.POD_PHASE_CHANGED,
                    pod_name, container_name=None,
                    data={'phase': raw_event.status['phase']},
                    cluster_time=None, local_time=datetime.datetime.now(),
                    raw_event=raw_event
                )
                self._log_event_and_callback(logged_event)

        # conditions change
        if 'conditions' in raw_event.status:
            for condition in raw_event.status['conditions']:
                last_condition = None
                if pod_name in self.last_raw_event_per_pod \
                        and 'conditions' in self.last_raw_event_per_pod[pod_name].status:

                    last_condition = next(
                        (lc for lc in self.last_raw_event_per_pod[pod_name].status['conditions'] if
                         lc['type'] == condition['type']), None)

                filter_keys = ['status', 'reason', 'message']
                if not equal_dicts(condition, last_condition, filter_keys):

                    cluster_time = None if 'lastTransitionTime' not in condition else \
                        datetime.datetime.strptime(condition['lastTransitionTime'], '%Y-%m-%dT%H:%M:%SZ')

                    data = {'type': condition['type']}
                    data.update(filtered_dict(condition, filter_keys))

                    logged_event = PodObjectLoggedEvent(
                        PodObjectLoggedEvent.POD_CONDITION_CHANGED,
                        pod_name, container_name=None,
                        data=data,
                        cluster_time=cluster_time, local_time=datetime.datetime.now(),
                        raw_event=raw_event
                    )
                    self._log_event_and_callback(logged_event)

        # containerStatuses change
        if 'containerStatuses' in raw_event.status:
            for container_status in raw_event.status['containerStatuses']:
                last_container_status = None
                if pod_name in self.last_raw_event_per_pod \
                        and 'containerStatuses' in self.last_raw_event_per_pod[pod_name].status:

                    last_container_status = next(
                        (lcs for lcs in self.last_raw_event_per_pod[pod_name].status['containerStatuses'] if
                         lcs['name'] == container_status['name']), None)

                # special cases
                # state - general container state change
                # started - Startup Probe passed/failed
                # ready - ReadinessP robe passed/failed
                # restartCount - Restart event
                # TODO add last_state to all container events
                for logged_event_type, filter_keys in [
                    (PodObjectLoggedEvent.CONTAINER_STATE_CHANGED, ['state']),
                    (PodObjectLoggedEvent.CONTAINER_STARTUP_PROBE_STATE_CHANGED, ['started']),
                    (PodObjectLoggedEvent.CONTAINER_READINESS_PROBE_STATE_CHANGED, ['ready']),
                    (PodObjectLoggedEvent.CONTAINER_RESTART_COUNT_CHANGED, ['restartCount'])]:

                    if not equal_dicts(container_status, last_container_status, filter_keys):
                        container_name = container_status['name']
                        logged_event = PodObjectLoggedEvent(
                            logged_event_type,
                            pod_name, container_name=container_name,
                            data=filtered_dict(container_status, filter_keys + ['last_state']),
                            cluster_time=None, local_time=datetime.datetime.now(),
                            raw_event=raw_event
                        )
                        self._log_event_and_callback(logged_event)

        self.last_raw_event_per_pod[pod_name] = raw_event
