import datetime
from perf.kube_watcher.event.raw.kube_event.kube_raw_event import KubeRawEvent
from perf.kube_watcher.event.logged.kube_event.pod_kube_logged_event import PodKubeLoggedEvent
from perf.kube_watcher.event.logged.pod_events_log import PodEventsLog


class PodKubeEventsLog(PodEventsLog):
    def __init__(self, pod_event_queues, callbacks):
        super(PodKubeEventsLog, self).__init__(pod_event_queues, callbacks)

        self.unhealthy_count = {}

    def update_state(self, raw_event):
        if not isinstance(raw_event, KubeRawEvent):
            raise ValueError(f'Unsupported raw_event class: {raw_event.__class__.__name__}')

        if raw_event.involved_object_kind != 'Pod':
            raise ValueError(f'Unsupported involved_object_kind: {raw_event.involved_object_kind}')

        if raw_event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown raw_event.type: {raw_event.type}')

        if raw_event.object_kind != 'Event':
            raise ValueError(f'Unknown raw_event.kind: {raw_event.type}')

        if raw_event.type not in ['ADDED', 'MODIFIED']:
            # v1.Event DELETE event deletes Event object, has nothing to do with Pod
            return

        pod_name = raw_event.involved_object_name
        reason = raw_event.object_reason
        count = raw_event.object_count
        message = raw_event.object_message
        cluster_time = raw_event.object_last_timestamp # datetime
        container_name = None
        if raw_event.involved_object_field_path:
            # Example string: spec.containers{container_name}
            split = raw_event.involved_object_field_path.split('spec.containers')[1]
            container_name = split[1:-1]

        # Unhealthy special case
        if reason == 'Unhealthy':
            if pod_name not in self.unhealthy_count:
                self.unhealthy_count[pod_name] = {container_name: {'startup': 0, 'liveness': 0, 'readiness': 0}}

            unhealthy_startup_count = self.unhealthy_count[pod_name][container_name]['startup']
            unhealthy_liveness_count = self.unhealthy_count[pod_name][container_name]['liveness']
            unhealthy_readiness_count = self.unhealthy_count[pod_name][container_name]['readiness']

            # validate consistency
            # if unhealthy_startup_count + unhealthy_liveness_count + 1 != int(count):
            #     raise ValueError(
            #         f'Unhealthy count missmatch: s {unhealthy_startup_count}, l {unhealthy_liveness_count}, total {count}')

            # Parse msg to get unhealthy type
            if message.startswith('Startup'):
                reason = 'UnhealthyStartup'
                count = unhealthy_startup_count + 1
                self.unhealthy_count[pod_name][container_name]['startup'] = count
            elif message.startswith('Liveness'):
                reason = 'UnhealthyLiveness'
                count = unhealthy_liveness_count + 1
                self.unhealthy_count[pod_name][container_name]['liveness'] = count
            elif message.startswith('Readiness'):
                reason = 'UnhealthyReadiness'
                count = unhealthy_readiness_count + 1
                self.unhealthy_count[pod_name][container_name]['readiness'] = count
            else:
                raise ValueError(f'Unknown Unhealthy message: {message}')

        data = {
            'reason': reason,
            'count': count,
            'message': message,
        }

        logged_event_type = PodKubeLoggedEvent.CONTAINER_EVENT if container_name else PodKubeLoggedEvent.POD_EVENT
        logged_event = PodKubeLoggedEvent(
            logged_event_type,
            pod_name, container_name=container_name,
            data=data,
            cluster_time=cluster_time, local_time=datetime.datetime.now(),
            raw_event=raw_event
        )
        self._log_event_and_callback(logged_event)

    def get_unhealthy_liveness_count(self, pod_name, container_name):
        return self.unhealthy_count[pod_name][container_name]['liveness']

    def get_unhealthy_startup_count(self, pod_name, container_name):
        return self.unhealthy_count[pod_name][container_name]['startup']

    def get_unhealthy_readiness_count(self, pod_name, container_name):
        return self.unhealthy_count[pod_name][container_name]['readiness']
