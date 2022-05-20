# {
#     "type": "MODIFIED",
#     "name": "data-feed-bybit-perpetual-cca5766921-ss-0",
#     "status": {
#         "phase": "Pending",
#         "conditions": [
#             {
#                 "type": "Initialized",
#                 "status": "True",
#                 "lastProbeTime": null,
#                 "lastTransitionTime": "2022-05-18T15:25:38Z"
#             },
#             {
#                 "type": "Ready",
#                 "status": "False",
#                 "lastProbeTime": null,
#                 "lastTransitionTime": "2022-05-18T15:25:38Z",
#                 "reason": "ContainersNotReady",
#                 "message": "containers with unready status: [redis redis-exporter data-feed-container]"
#             },
#             {
#                 "type": "ContainersReady",
#                 "status": "False",
#                 "lastProbeTime": null,
#                 "lastTransitionTime": "2022-05-18T15:25:38Z",
#                 "reason": "ContainersNotReady",
#                 "message": "containers with unready status: [redis redis-exporter data-feed-container]"
#             },
#             {
#                 "type": "PodScheduled",
#                 "status": "True",
#                 "lastProbeTime": null,
#                 "lastTransitionTime": "2022-05-18T15:25:38Z"
#             }
#         ],
#         "containerStatuses": [
#             {
#                 "name": "data-feed-container",
#                 "state": {
#                     "waiting": {
#                         "reason": "ContainerCreating"
#                     }
#                 },
#                 "lastState": {},
#                 "ready": false,
#                 "restartCount": 0,
#                 "image": "050011372339.dkr.ecr.ap-northeast-1.amazonaws.com/anov/svoe_data_feed:v1.0.3",
#                 "imageID": "",
#                 "started": false
#             },
#             {
#                 "name": "redis",
#                 "state": {
#                     "waiting": {
#                         "reason": "ContainerCreating"
#                     }
#                 },
#                 "lastState": {},
#                 "ready": false,
#                 "restartCount": 0,
#                 "image": "redis:alpine",
#                 "imageID": "",
#                 "started": false
#             },
#             {
#                 "name": "redis-exporter",
#                 "state": {
#                     "waiting": {
#                         "reason": "ContainerCreating"
#                     }
#                 },
#                 "lastState": {},
#                 "ready": false,
#                 "restartCount": 0,
#                 "image": "oliver006/redis_exporter:latest",
#                 "imageID": "",
#                 "started": false
#             }
#         ]
#     }
# }

import queue
from ..utils import equal_dicts, filtered_dict

class PodObjectEvent:
    def __init__(self, raw_event):
        status = raw_event['raw_object']['status']
        status_filtered = {}
        if 'phase' in status:
            status_filtered['phase'] = status['phase']
        if 'conditions' in status:
            status_filtered['conditions'] = status['conditions']
        if 'containerStatuses' in status:
            status_filtered['containerStatuses'] = status['containerStatuses']

        self.type = raw_event['type']
        self.pod_name = raw_event['raw_object']['metadata']['name']
        self.status = status_filtered


class PodObjectEventsLog:
    # tracks only Pod related events
    def __init__(self):
        self.max_queue_size = 100
        self.event_queue = queue.Queue(self.max_queue_size)
        self.last_event = None
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    # TODO pod_name to callback
    def update_state(self, event):
        if event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown event.type: {event.type}')

        pod_name = event.pod_name

        if event.type == 'DELETED':
            logged_event_type = 'POD_DELETED'
            logged_event_key = pod_name # TODO move away to separate fields
            logged_event_value = ''
            timestamp = None
            self.event_queue.put((logged_event_type, logged_event_key, logged_event_value, timestamp))

            for callback in self.callbacks:
                callback(logged_event_type, logged_event_key, logged_event_value, timestamp)

            self.last_event = event
            return

        # phase change
        if 'phase' in event.status:
            if not self.last_event \
                    or 'phase' not in self.last_event.status \
                    or self.last_event.status['phase'] != event.status['phase']:
                logged_event_type = 'POD_PHASE_CHANGED' # TODO enum and separate class
                logged_event_key = 'phase'
                logged_event_value = event.status['phase']
                # TODO timestamp
                timestamp = None
                # TODO make object for event
                self.event_queue.put((logged_event_type, logged_event_key, logged_event_value, timestamp))
                for callback in self.callbacks:
                    callback(logged_event_type, logged_event_key, logged_event_value, timestamp)

        # conditions change
        if 'conditions' in event.status:
            for condition in event.status['conditions']:
                last_condition = None
                if self.last_event and 'conditions' in self.last_event.status:
                    for lc in self.last_event.status['conditions']:
                        if lc['type'] == condition['type']:
                            last_condition = lc
                            break

                filter_keys = ['status', 'reason', 'message']
                if not equal_dicts(condition, last_condition, filter_keys):
                    logged_event_type = 'POD_CONDITION_CHANGED'
                    logged_event_key = condition['type']
                    logged_event_value = filtered_dict(condition, filter_keys)
                    timestamp = None if 'lastTransitionTime' not in condition else condition['lastTransitionTime']
                    self.event_queue.put((logged_event_type, logged_event_key, logged_event_value, timestamp))
                    for callback in self.callbacks:
                        callback(logged_event_type, logged_event_key, logged_event_value, timestamp)

        # containerStatuses change
        if 'containerStatuses' in event.status:
            for container_status in event.status['containerStatuses']:
                last_container_status = None
                if self.last_event and 'containerStatuses' in self.last_event.status:
                    for lcs in self.last_event.status['containerStatuses']:
                        if lcs['name'] == container_status['name']:
                            last_container_status = lcs
                            break

                for logged_event_type, filter_keys in [
                    ('CONTAINER_STATE_CHANGED', ['state']),
                    ('CONTAINER_STARTUP_PROBE_STATE_CHANGED', ['started']),
                    ('CONTAINER_READINESS_PROBE_STATE_CHANGED', ['ready']),
                    ('CONTAINER_RESTART_COUNT_CHANGED', ['restartCount'])
                ]:
                    # special cases
                    # state - general container state change
                    # started - Startup Probe passed/failed
                    # ready - ReadinessP robe passed/failed
                    # restartCount - Restart event
                    if not equal_dicts(container_status, last_container_status, filter_keys):
                        # logged_event_type = 'CONTAINER_STATUS_CHANGED' # TODO separate type
                        logged_event_key = container_status['name']# container name
                        logged_event_value = filtered_dict(container_status, filter_keys)
                        # TODO timestamp
                        timestamp = None
                        self.event_queue.put((logged_event_type, logged_event_key, logged_event_value, timestamp))
                        for callback in self.callbacks:
                            callback(logged_event_type, logged_event_key, logged_event_value, timestamp)

        self.last_event = event
