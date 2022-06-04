import json
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


class KubeWatcher:
    def __init__(self, core_api, callbacks):

        self.running = False
        self.core_api = core_api
        self.event_queues_per_pod = {}
        self.event_queues_per_node = {}

        self.kube_events_watcher = None
        self.kube_events_thread = None
        self.pod_kube_events_log = PodKubeEventsLog(self.event_queues_per_pod, callbacks)
        self.node_kube_events_log = NodeKubeEventsLog(self.event_queues_per_node, callbacks)

        self.pod_object_events_watcher = None
        self.pod_object_events_thread = None
        self.pod_object_events_log = PodObjectEventsLog(self.event_queues_per_pod, callbacks)

        self.node_object_events_watcher = None
        self.node_object_events_thread = None
        self.node_object_events_log = NodeObjectEventsLog(self.event_queues_per_pod, callbacks)

    def _watch_kube_events_blocking(self):
        self.kube_events_watcher = kubernetes.watch.Watch()
        last_resource_version = None
        first_init = True
        should_filter_stale = True
        while self.running:
            start_time = time.time()
            if first_init or last_resource_version is None:
                # First call, resource_version is unset, events need to be filtered by timestamp
                # TODO add field selector to limit by namespace/involved_object_kind
                stream = self.kube_events_watcher.stream(
                    self.core_api.list_event_for_all_namespaces,
                    watch=True,
                    timeout_seconds=10
                )
                first_init = False
            else:
                should_filter_stale = False
                # TODO add field selector to limit by namespace/involved_object_kind
                stream = self.kube_events_watcher.stream(
                    self.core_api.list_event_for_all_namespaces,
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
                if should_filter_stale and first_init:
                    # filter stale and synthetic events for first init
                    delta = start_time - raw_event.object_last_timestamp.timestamp()
                    if delta > 5:
                        # if event is older 5s - drop
                        continue
                if raw_event.involved_object_kind == 'Pod':
                    self.pod_kube_events_log.update_state(raw_event)
                elif raw_event.involved_object_kind == 'Node':
                    self.node_kube_events_log.update_state(raw_event)
            if message_count == 0:
                # in case generator has no events, sleep until next call to kube to avoid empty cpu cycles
                time.sleep(0.5)

    def watch_kube_events(self):
        self.kube_events_thread = threading.Thread(target=self._watch_kube_events_blocking)
        self.kube_events_thread.start()

    def _watch_pod_object_events_blocking(self, namespace):
        self.pod_object_events_watcher = kubernetes.watch.Watch()
        while self.running:
            for message in self.pod_object_events_watcher.stream(
                self.core_api.list_pod_for_all_namespaces,
                watch=True,
                field_selector=f'metadata.namespace={namespace}',
                timeout_seconds=10
            ):
                if not self.running:
                    break
                raw_event = PodObjectRawEvent(message)
                self.pod_object_events_log.update_state(raw_event)

    def watch_pod_object_events(self, namespace):
        self.pod_object_events_thread = threading.Thread(target=self._watch_pod_object_events_blocking, args=(namespace,))
        self.pod_object_events_thread.start()

    def _watch_node_object_events_blocking(self):
        self.node_object_events_watcher = kubernetes.watch.Watch()
        while self.running:
            for message in self.node_object_events_watcher.stream(
                self.core_api.list_node,
                watch=True,
                timeout_seconds=10
            ):
                if not self.running:
                    break

                raw_event = NodeObjectRawEvent(message)
                self.node_object_events_log.update_state(raw_event)

    def watch_node_object_events(self):
        self.node_object_events_thread = threading.Thread(target=self._watch_node_object_events_blocking())
        self.node_object_events_thread.start()

    def start(self):
        # https://github.com/kubernetes-client/python/issues/728
        # https://www.programcreek.com/python/example/111707/kubernetes.watch.Watch
        if self.running:
            return
        print(f'KubeWatcher started')
        self.running = True
        self.watch_pod_object_events(DATA_FEED_NAMESPACE)
        self.watch_kube_events()
        self.watch_node_object_events()

    def stop(self):
        if not self.running:
            return
        self.running = False
        print(f'Stopping Kube Watcher...')
        for watcher, thread, name in [
            (self.kube_events_watcher, self.kube_events_thread, 'kube_events'),
            (self.pod_object_events_watcher, self.pod_object_events_thread, 'pod_object_events'),
            (self.node_object_events_watcher, self.node_object_events_thread, 'node_object_events')
        ]:
            # TODO nulify each object
            if watcher:
                watcher.stop()
                print(f'Stopping {name}_watcher stopped')
            if thread:
                print(f'Joining {name}_thread')
                thread.join()
                print(f'{name}_thread joined')

        print(f'Kube Watcher stopped')
