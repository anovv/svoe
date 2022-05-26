# core_api.list_namespaced_event:
#     # ADDED, MODIFIED (Unhealthy: object.count, BackOff: object.count)
#         'type': raw_event['type'],
#         # Event
#         'object.kind': raw_event['object'].kind,
#         # Normal, Warning
#         'object.type': raw_event['object'].type,
#         # Normal:
#         #   StatefulSet:
#         #     SuccessfulCreate: "create Pod {pod_name} in StatefulSet {ss_name} successful"
#         #     SuccessfulDelete: "delete Pod {pod_name} in StatefulSet {ss_name} successful"
#         #   Pod:
#         #     Scheduled: "Successfully assigned {ns}/{pod_name} to {node_name}
#         #     per container:
#         #       Pulled: "Container image {image_name} already present on machine"
#         #       Created: "Created container {container_name}"
#         #       Started: "Started container {container_name}"
#         #       Pulling: "Pulling image {image_name}
#         #       Killing: "Stopping container {container_name}"
#         #       BackOff:  "Back-off restarting failed container"
#         # Warning:
#         #   Pod:
#         #     per container:
#         #       Unhealthy:  "Liveness probe failed: Get \"http://10.244.1.38:1234/health\": context deadline exceeded (Client.Timeout exceeded while awaiting headers)"
#         #       or "Startup probe failed: HTTP probe failed with statuscode: 500"
#         'object.reason': raw_event['object'].reason,
#         'object.message': raw_event['object'].message,
#         # Pod and StatefulSet
#         'object.count': raw_event['object'].count,
#         # null
#         'object.action': raw_event['object'].action,
#         # Pod, StatefulSet
#         'object.involved_object.kind': raw_event['object'].involved_object.kind,
#         # pod or ss name
#         'object.involved_object.name': raw_event['object'].involved_object.name,
#         # StatefulSet: no field,
#         # Pod: spec.containers{container_name} for Pulled, Created, Started, Pulling, Unhealthy, Killing
#         'object.involved_object.field_path': raw_event['object'].involved_object.field_path,
#         'object.first_timestamp': raw_event['object'].first_timestamp,
#         'object.last_timestamp': raw_event['object'].last_timestamp,

import datetime
from .pod_logged_event import PodKubeLoggedEvent, PodEventsLog


class PodKubeRawEvent:
    def __init__(self, raw_event):
        self.type = raw_event['type']
        self.object_kind = raw_event['object'].kind
        self.object_type = raw_event['object'].type
        self.object_reason = raw_event['object'].reason
        self.object_message = raw_event['object'].message
        self.object_count = raw_event['object'].count
        self.involved_object_kind = raw_event['object'].involved_object.kind
        self.involved_object_name = raw_event['object'].involved_object.name
        self.involved_object_field_path = raw_event['object'].involved_object.field_path
        self.object_first_timestamp = raw_event['object'].first_timestamp
        self.object_last_timestamp = raw_event['object'].last_timestamp
        self.resource_version = raw_event['object'].metadata.resource_version


class PodKubeEventsLog(PodEventsLog):
    def __init__(self, pod_event_queues, callbacks):
        super().__init__(pod_event_queues, callbacks)

        self.unhealthy_count = {}

    def update_state(self, raw_event):
        if not isinstance(raw_event, PodKubeRawEvent):
            raise ValueError(f'Unsupported raw_event class: {raw_event.__class__.__name__}')

        if raw_event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown raw_event.type: {raw_event.type}')

        if raw_event.object_kind != 'Event':
            raise ValueError(f'Unknown raw_event.kind: {raw_event.type}')

        if raw_event.type not in ['ADDED', 'MODIFIED'] or raw_event.involved_object_kind != 'Pod':
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
                self.unhealthy_count[pod_name] = {container_name: {'startup': 0, 'liveness': 0}}

            unhealthy_startup_count = self.unhealthy_count[pod_name][container_name]['startup']
            unhealthy_liveness_count = self.unhealthy_count[pod_name][container_name]['liveness']

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

    def get_unhealthy_count(self):
        return self.unhealthy_count
