import threading

from ..defines import *
import time
import kubernetes
from .pod_kube_events_log import PodKubeRawEvent, PodKubeEventsLog
from .pod_object_events_log import PodObjectRawEvent, PodObjectEventsLog


class KubeWatcher:
    def __init__(self, core_api, callbacks):

        self.running = False
        self.core_api = core_api
        self.event_queues_per_pod = {}

        self.pod_kube_events_watcher = None
        self.pod_kube_events_thread = None
        self.pod_kube_events_log = PodKubeEventsLog(self.event_queues_per_pod, callbacks)

        self.pod_object_events_watcher = None
        self.pod_object_events_thread = None
        self.pod_object_events_log = PodObjectEventsLog(self.event_queues_per_pod, callbacks)

    def _watch_pod_kube_events_blocking(self):
        self.pod_kube_events_watcher = kubernetes.watch.Watch()
        while self.running:
            start_time = time.time()
            for message in self.pod_kube_events_watcher.stream(
                self.core_api.list_event_for_all_namespaces,
                watch=True,
                field_selector=f'metadata.namespace={DATA_FEED_NAMESPACE}',
                timeout_seconds=10
            ):
                if not self.running:
                    break
                raw_event = PodKubeRawEvent(message)
                # drop stale events
                delta = start_time - raw_event.object_last_timestamp.timestamp()
                # delta should be magnitude of latency
                if delta > 1:
                    continue
                self.pod_kube_events_log.update_state(raw_event)

    def watch_pod_kube_events(self):
        self.pod_kube_events_thread = threading.Thread(target=self._watch_pod_kube_events_blocking)
        self.pod_kube_events_thread.start()

    def _watch_pod_object_events_blocking(self):
        self.pod_object_events_watcher = kubernetes.watch.Watch()
        while self.running:
            for message in self.pod_object_events_watcher.stream(
                self.core_api.list_pod_for_all_namespaces,
                watch=True,
                field_selector=f'metadata.namespace={DATA_FEED_NAMESPACE}',
                timeout_seconds=10
            ):
                if not self.running:
                    break
                raw_event = PodObjectRawEvent(message)
                self.pod_object_events_log.update_state(raw_event)

    def watch_pod_object_events(self):
        self.pod_object_events_thread = threading.Thread(target=self._watch_pod_object_events_blocking)
        self.pod_object_events_thread.start()

    def start(self):
        # https://github.com/kubernetes-client/python/issues/728
        # https://www.programcreek.com/python/example/111707/kubernetes.watch.Watch
        if self.running:
            return
        print(f'KubeWatcher started')
        self.running = True
        self.watch_pod_object_events()
        self.watch_pod_kube_events()

    def stop(self):
        if not self.running:
            return
        self.running = False
        # TODO finish/cancel running tasks in asyncio loop and close loop
        print(f'Stopping Kube Watcher...')
        if self.pod_kube_events_watcher:
            self.pod_kube_events_watcher.stop()
            self.pod_kube_events_watcher = None
            print(f'Stopping pod_kube_events_watcher stopped')

        if self.pod_kube_events_thread:
            print(f'Joining pod_kube_events_thread ...')
            self.pod_kube_events_thread.join()
            self.pod_kube_events_thread = None
            print(f'Stopping pod_kube_events_thread stopped')

        if self.pod_object_events_watcher:
            self.pod_object_events_watcher.stop()
            self.pod_object_events_watcher = None
            print(f'pod_object_events_watcher stopped')

        if self.pod_object_events_thread:
            print(f'Joining pod_object_events_thread ...')
            self.pod_object_events_thread.join()
            self.pod_object_events_thread = None
            print(f'pod_object_events_thread stopped')

        print(f'Kube Watcher stopped')
