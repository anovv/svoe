# scale_up:
#     core_api.list_namespaced_event:
#         # ADDED, MODIFIED (Unhealthy: object.count, BackOff: object.count)
#             'type': raw_event['type'],
#             # Event
#             'object.kind': raw_event['object'].kind,
#             # Normal, Warning
#             'object.type': raw_event['object'].type,
#             # Normal:
#             #   StatefulSet:
#             #     SuccessfulCreate: "create Pod {name} in StatefulSet {name} successful"
#             #     SuccessfulDelete: "delete Pod data-feed-binance-spot-eb540d90be-ss-0 in StatefulSet data-feed-binance-spot-eb540d90be-ss successful"
#             #   Pod:
#             #     Scheduled: "Successfully assigned data-feed/data-feed-binance-spot-eb540d90be-ss-0 to minikube-1-m02
#             #     per container:
#             #       Pulled: "Container image \"redis:alpine\" already present on machine"
#             #       Created: "Created container redis"
#             #       Started: "Started container redis"
#             #       Pulling: "Pulling image \"oliver006/redis_exporter:latest\""
#             #       Killing: "Stopping container redis"
#             #       BackOff:  "Back-off restarting failed container"
#             # Warning:
#             #   Pod:
#             #     per container:
#             #       Unhealthy:  "Liveness probe failed: Get \"http://10.244.1.38:1234/health\": context deadline exceeded (Client.Timeout exceeded while awaiting headers)"
#             #       or "Startup probe failed: HTTP probe failed with statuscode: 500"
#             'object.reason': raw_event['object'].reason,
#             'object.message': raw_event['object'].message,
#             # Pod and StatefulSet
#             'object.count': raw_event['object'].count,
#             # null
#             'object.action': raw_event['object'].action,
#             # Pod, StatefulSet
#             'object.involved_object.kind': raw_event['object'].involved_object.kind,
#             # pod or ss name
#             'object.involved_object.name': raw_event['object'].involved_object.name,
#             # StatefulSet: no field,
#             # Pod: spec.containers{container_name} for Pulled, Created, Started, Pulling, Unhealthy, Killing
#             'object.involved_object.field_path': raw_event['object'].involved_object.field_path,
#             'object.first_timestamp': raw_event['object'].first_timestamp,
#             'object.last_timestamp': raw_event['object'].last_timestamp,

import queue


class PodKubeEvent:
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


class PodKubeEventsLog:
    # tracks only Pod related events
    def __init__(self):
        # log example (per pod)
        # {
        #    reason, count, message, timestamp
        #   'global' = [('Scheduled', 1, 'bla bla', 1234567), ...]
        #
        #   'per_container': {
        #       'redis' = [('Unhealthy', 10, 'startup probe failed', 1234567), ...]
        #    }
        # }
        self.max_queue_size = 100
        self.events_log = {}
        self.unhealthy_count = {}

    def update_state(self, event):
        if event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown event.type: {event.type}')
        if event.object_kind != 'Event':
            raise ValueError(f'Unknown event.kind: {event.type}')

        if event.type not in ['ADDED', 'MODIFIED'] or event.involved_object_kind != 'Pod':
            return
        pod_name = event.involved_object_name
        reason = event.object_reason
        count = event.object_count
        message = event.object_message
        last_timestamp = event.object_last_timestamp # datetime
        container_name = None
        if event.involved_object_field_path:
            # Example string: spec.containers{container_name}
            # TODO add valid containers validation?
            split = event.involved_object_field_path.split('spec.containers')[1]
            container_name = split[1:-1]

        if pod_name not in self.events_log:
            self.events_log[pod_name] = {
                'global': queue.Queue(maxsize=self.max_queue_size),
                'per_container': {},
            }

        if container_name:
            if container_name not in self.events_log[pod_name]['per_container']:
                self.events_log[pod_name]['per_container'][container_name] = queue.Queue(maxsize=self.max_queue_size)
            q = self.events_log[pod_name]['per_container'][container_name]
        else:
            q = self.events_log[pod_name]['global']

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

        if q.empty() or (q.queue[-1][0] != reason or q.queue[-1][1] != count or q.queue[-1][2] != message):
            # handle callbacks here
            q.put((reason, count, message, last_timestamp))
            # TODO callbacks here.
            print(f'New event: {q.queue[-1]}')
        else:
            print(f'Dropped event: {(reason, count, message, last_timestamp)}')

