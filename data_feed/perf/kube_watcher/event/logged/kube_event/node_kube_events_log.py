import datetime

from perf.kube_watcher.event.raw.kube_event.kube_raw_event import KubeRawEvent
from perf.kube_watcher.event.logged.node_events_log import NodeEventsLog
from perf.kube_watcher.event.logged.kube_event.node_kube_logged_event import NodeKubeLoggedEvent


class NodeKubeEventsLog(NodeEventsLog):
    def __init__(self, pod_event_queues, callbacks):
        super(NodeKubeEventsLog, self).__init__(pod_event_queues, callbacks)

    def update_state(self, raw_event):
        if not isinstance(raw_event, KubeRawEvent):
            raise ValueError(f'Unsupported raw_event class: {raw_event.__class__.__name__}')

        if raw_event.involved_object_kind != 'Node':
            raise ValueError(f'Unsupported involved_object_kind: {raw_event.involved_object_kind}')

        if raw_event.type not in ['ADDED', 'MODIFIED', 'DELETED']:
            raise ValueError(f'Unknown raw_event.type: {raw_event.type}')

        if raw_event.object_kind != 'Event':
            raise ValueError(f'Unknown raw_event.kind: {raw_event.type}')

        if raw_event.type not in ['ADDED', 'MODIFIED']:
            # v1.Event DELETE event deletes Event object, has nothing to do with Node
            return

        node_name = raw_event.involved_object_name
        reason = raw_event.object_reason
        count = raw_event.object_count
        message = raw_event.object_message
        cluster_time = raw_event.object_last_timestamp  # datetime

        data = {
            'reason': reason,
            'count': count,
            'message': message
        }

        logged_event = None
        # {'reason': 'SystemOOM', 'message': 'System OOM encountered, victim process: svoe_data_feed_, pid: 160906'}
        if reason == 'SystemOOM':
            try:
                pid = message.split('pid:')[1].strip()
                data.update({'pid': pid})
                logged_event = NodeKubeLoggedEvent(
                    NodeKubeLoggedEvent.OOM_VICTIM_PROCESS,
                    node_name,
                    data=data,
                    cluster_time=cluster_time, local_time=datetime.datetime.now(),
                    raw_event=raw_event
                )
            except Exception as e:
                print(e)
                print(f'[NodeKubeEventsLog] Unable to parse SystemOOM message: {message}')
        # {'reason': 'OOMKilling', 'message': '(can be more stuff herer from kube) Killed process 160111 (svoe_data_feed_) total-vm:842716kB, anon-rss:132948kB, file-rss:0kB, shmem-rss:0kB'}
        elif reason == 'OOMKilling':
            try:
                first = 'Killed process'
                last = 'total-vm'
                start = message.index(first) + len(first)
                end = message.index(last, start)
                s = message[start: end].strip() # 160111 (svoe_data_feed_)
                split = s.split(' ')
                pid = split[0]
                pname = split[1][1:-1] # remove ()
                data.update({'pid': pid, 'pname': pname})
                logged_event = NodeKubeLoggedEvent(
                    NodeKubeLoggedEvent.OOM_KILLED_PROCESS,
                    node_name,
                    data=data,
                    cluster_time=cluster_time, local_time=datetime.datetime.now(),
                    raw_event=raw_event
                )
            except Exception as e:
                print(e)
                print(f'[NodeKubeEventsLog] Unable to parse OOMKilling message: {message}')

        # default
        if logged_event is None:
            logged_event = NodeKubeLoggedEvent(
                NodeKubeLoggedEvent.NODE_EVENT,
                node_name,
                data=data,
                cluster_time=cluster_time, local_time=datetime.datetime.now(),
                raw_event=raw_event
            )
        self._log_event_and_callback(logged_event)
