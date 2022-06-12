import threading
import time
import kubernetes

from perf.defines import DATA_FEED_NAMESPACE
from perf.kube_watcher.event.raw.kube_event.kube_raw_event import KubeRawEvent
from perf.kube_watcher.event.raw.object.pod_object_raw_event import PodObjectRawEvent
from perf.kube_watcher.event.raw.object.node_object_raw_event import NodeObjectRawEvent


# channels names
CHANNEL_NODE_KUBE_EVENTS = 'CHANNEL_NODE_KUBE_EVENTS'
CHANNEL_NODE_OBJECT_EVENTS = 'CHANNEL_NODE_OBJECT_EVENTS'
CHANNEL_DF_POD_KUBE_EVENTS = 'CHANNEL_DF_POD_KUBE_EVENTS'
CHANNEL_DF_POD_OBJECT_EVENTS = 'CHANNEL_DF_POD_OBJECT_EVENTS'


class KubeWatcher:
    def __init__(self, core_api, kube_watcher_state):
        self.running = False
        self.core_api = core_api
        self.kube_watcher_state = kube_watcher_state
        self.channels = {}

        # init channels
        for channel, watch_blocking, namespace in [
            (CHANNEL_NODE_KUBE_EVENTS, self._watch_node_kube_events_blocking, None),
            (CHANNEL_NODE_OBJECT_EVENTS, self._watch_node_object_events_blocking, None),
            (CHANNEL_DF_POD_KUBE_EVENTS, self._watch_pod_kube_events_blocking, DATA_FEED_NAMESPACE),
            (CHANNEL_DF_POD_OBJECT_EVENTS, self._watch_pod_object_events_blocking, DATA_FEED_NAMESPACE),
        ]:
            watcher = kubernetes.watch.Watch()
            if namespace:
                thread_args = (watcher, self.kube_watcher_state.event_logs_per_channel[channel], namespace)
            else:
                thread_args = (watcher, self.kube_watcher_state.event_logs_per_channel[channel])

            self.channels[channel] = {
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
        # https://stackoverflow.com/questions/52717497/correct-way-to-use-kubernetes-watches
        # TODO make it bounded to store for specific time period to avoid memory leak
        seen_resource_versions = set()
        event_list = self.core_api.list_event_for_all_namespaces(field_selector=field_selector)
        last_resource_version = event_list.metadata.resource_version
        while self.running:
            message_count = 0
            for message in watcher.stream(
                self.core_api.list_event_for_all_namespaces,
                field_selector=field_selector,
                watch=True,
                resource_version=last_resource_version,
                timeout_seconds=10
            ):
                message_count += 1
                if not self.running:
                    break
                raw_event = KubeRawEvent(message)
                last_resource_version = raw_event.resource_version
                if last_resource_version in seen_resource_versions:
                    continue
                seen_resource_versions.add(last_resource_version)

                # if raw_event.involved_object_kind == 'Node':
                #     print(f'[REG][{raw_event.type}][{raw_event.object_count}] Node Kube: {raw_event.object_message}')

                events_log.update_state(raw_event)

            if message_count == 0:
                # in case generator has no events, sleep until next call to kube to avoid empty cpu cycles
                time.sleep(0.5)

    def _watch_pod_object_events_blocking(self, watcher, events_log, namespace):
        while self.running:
            message_count = 0
            for message in watcher.stream(
                self.core_api.list_pod_for_all_namespaces,
                watch=True,
                field_selector=f'metadata.namespace={namespace}',
                timeout_seconds=10
            ):
                message_count += 1
                if not self.running:
                    break
                raw_event = PodObjectRawEvent(message)
                events_log.update_state(raw_event)

            if message_count == 0:
                # in case generator has no events, sleep until next call to kube to avoid empty cpu cycles
                time.sleep(0.5)

    def _watch_node_object_events_blocking(self, watcher, events_log):
        while self.running:
            message_count = 0
            for message in watcher.stream(
                self.core_api.list_node,
                watch=True,
                timeout_seconds=10
            ):
                message_count += 1
                if not self.running:
                    break
                raw_event = NodeObjectRawEvent(message)
                events_log.update_state(raw_event)

            if message_count == 0:
                # in case generator has no events, sleep until next call to kube to avoid empty cpu cycles
                time.sleep(0.5)

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

        # TODO clean kube_watcher_state ?

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
