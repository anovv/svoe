import threading

from perf.defines import DATA_FEED_NAMESPACE
import time
import kubernetes
from perf.kube_watcher.event.raw.kube_event.kube_raw_event import KubeRawEvent
from perf.kube_watcher.event.raw.object.pod_object_raw_event import PodObjectRawEvent
from perf.kube_watcher.event.raw.object.node_object_raw_event import NodeObjectRawEvent

from perf.kube_watcher.event.logged.kube_event.pod_kube_events_log import PodKubeEventsLog
from perf.kube_watcher.event.logged.kube_event.node_kube_events_log import NodeKubeEventsLog

from perf.kube_watcher.event.logged.object.pod_object_events_log import PodObjectEventsLog
from perf.kube_watcher.event.logged.object.node_object_events_log import NodeObjectEventsLog

# channel names
CHANNEL_NODE_KUBE_EVENTS = 'CHANNEL_NODE_KUBE_EVENTS'
CHANNEL_NODE_OBJECT_EVENTS = 'CHANNEL_NODE_OBJECT_EVENTS'
CHANNEL_DF_POD_KUBE_EVENTS = 'CHANNEL_DF_POD_KUBE_EVENTS'
CHANNEL_DF_POD_OBJECT_EVENTS = 'CHANNEL_DF_POD_OBJECT_EVENTS'


class KubeWatcher:
    def __init__(self, core_api, callbacks):

        self.running = False
        self.core_api = core_api
        self.event_queues_per_pod = {}
        self.event_queues_per_node = {}

        self.callbacks = callbacks
        self.channels = {}

        # init channels
        for name, events_log, watch_blocking, namespace in [
            (CHANNEL_NODE_KUBE_EVENTS,
             NodeKubeEventsLog(self.event_queues_per_node, self.callbacks),
             self._watch_node_kube_events_blocking,
             None
             ),
            (CHANNEL_NODE_OBJECT_EVENTS,
             NodeObjectEventsLog(self.event_queues_per_node, self.callbacks),
             self._watch_node_object_events_blocking,
             None
             ),
            (CHANNEL_DF_POD_KUBE_EVENTS,
             PodKubeEventsLog(self.event_queues_per_pod, self.callbacks),
             self._watch_pod_kube_events_blocking,
             DATA_FEED_NAMESPACE,
             ),
            (CHANNEL_DF_POD_OBJECT_EVENTS,
             PodObjectEventsLog(self.event_queues_per_pod, self.callbacks),
             self._watch_pod_object_events_blocking,
             DATA_FEED_NAMESPACE,
             ),
        ]:
            watcher = kubernetes.watch.Watch()
            if namespace:
                thread_args = (watcher, events_log, namespace)
            else:
                thread_args = (watcher, events_log)

            self.channels[name] = {
                'events_log': events_log,
                'thread': threading.Thread(target=watch_blocking, args=thread_args),
                'watcher': watcher,
            }

    def _watch_node_kube_events_blocking(self, watcher, events_log):
        field_selector = f'involvedObject.kind=Node'
        self._watch_kube_events_blocking(watcher, field_selector, events_log)

    def _watch_pod_kube_events_blocking(self, watcher, events_log, namespace):
        field_selector=f'metadata.namespace={namespace},involvedObject.kind=Pod'
        self._watch_kube_events_blocking(watcher, field_selector, events_log)

    def _watch_kube_events_blocking(self, watcher, field_selector, events_log):
        last_resource_version = None
        first_init = True
        while self.running:
            start_time = time.time()
            if first_init or last_resource_version is None:
                # First call, resource_version is unset, events need to be filtered by timestamp
                stream = watcher.stream(
                    self.core_api.list_event_for_all_namespaces,
                    field_selector=field_selector,
                    watch=True,
                    timeout_seconds=10
                )
            else:
                stream = watcher.stream(
                    self.core_api.list_event_for_all_namespaces,
                    field_selector=field_selector,
                    watch=True,
                    resource_version=last_resource_version,
                    timeout_seconds=10
                )

            message_count = 0
            for message in stream:
                message_count += 1
                if not self.running:
                    break
                raw_event = KubeRawEvent(message)
                last_resource_version = raw_event.resource_version
                if first_init:
                    # filter stale and synthetic events for first init
                    delta = 0
                    if raw_event.object_last_timestamp:
                        delta = start_time - raw_event.object_last_timestamp.timestamp()
                    elif raw_event.object_first_timestamp:
                        delta = start_time - raw_event.object_first_timestamp.timestamp()
                    elif raw_event.event_time:
                        delta = start_time - raw_event.event_time.timestamp()
                    if delta > 5:
                        # if event is older 5s - drop
                        # TODO
                        # print(f'filtered {message_count}')
                        continue
                events_log.update_state(raw_event)
            first_init = False
            if message_count == 0:
                # in case generator has no events, sleep until next call to kube to avoid empty cpu cycles
                time.sleep(0.5)

    def _watch_pod_object_events_blocking(self, watcher, events_log, namespace):
        while self.running:
            for message in watcher.stream(
                self.core_api.list_pod_for_all_namespaces,
                watch=True,
                field_selector=f'metadata.namespace={namespace}',
                timeout_seconds=10
            ):
                if not self.running:
                    break
                raw_event = PodObjectRawEvent(message)
                events_log.update_state(raw_event)

    def _watch_node_object_events_blocking(self, watcher, events_log):
        while self.running:
            for message in watcher.stream(
                self.core_api.list_node,
                watch=True,
                timeout_seconds=10
            ):
                if not self.running:
                    break
                raw_event = NodeObjectRawEvent(message)
                events_log.update_state(raw_event)

    def start(self, channels):
        # https://github.com/kubernetes-client/python/issues/728
        # https://www.programcreek.com/python/example/111707/kubernetes.watch.Watch
        if self.running:
            return
        print(f'KubeWatcher started')
        self.running = True
        for name in channels:
            channel = self.channels[name]
            channel['thread'].start()

    def stop(self, channels):
        if not self.running:
            return
        self.running = False
        print(f'Stopping Kube Watcher...')

        for name in channels:
            channel = self.channels[name]
            watcher = channel['watcher']
            thread = channel['thread']
            watcher.stop()
            print(f'Stopping {name}_watcher stopped')
            print(f'Joining {name}_thread')
            thread.join()
            print(f'{name}_thread joined')
            del self.channels[name]

        print(f'Kube Watcher stopped')
