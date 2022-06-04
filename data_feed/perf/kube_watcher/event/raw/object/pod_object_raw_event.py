from perf.kube_watcher.event.raw.raw_event import RawEvent


class PodObjectRawEvent(RawEvent):
    def __init__(self, raw_event):
        super().__init__(raw_event)
        status = raw_event['raw_object']['status']
        status_filtered = {}
        if 'phase' in status:
            status_filtered['phase'] = status['phase']
        if 'conditions' in status:
            status_filtered['conditions'] = status['conditions']
        if 'containerStatuses' in status:
            status_filtered['containerStatuses'] = status['containerStatuses']

        self.pod_name = raw_event['raw_object']['metadata']['name']
        self.status = status_filtered

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
