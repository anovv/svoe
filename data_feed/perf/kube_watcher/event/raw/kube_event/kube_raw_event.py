from perf.kube_watcher.event.raw.raw_event import RawEvent


class KubeRawEvent(RawEvent):
    def __init__(self, raw_event):
        super(KubeRawEvent, self).__init__(raw_event)
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
        self.creation_timestamp = raw_event['object'].metadata.creation_timestamp
        self.event_time = raw_event['object'].event_time
        
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