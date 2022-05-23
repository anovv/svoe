import threading

from ..defines import *
import time
import json
import time
import kubernetes
import asyncio
from .pod_kube_events_log import PodKubeRawEvent, PodKubeEventsLog
from .pod_object_events_log import PodObjectRawEvent, PodObjectEventsLog


class KubeWatcher:
    def __init__(self, core_api, callbacks):
        self.pod_kube_events_watcher = None
        self.pod_object_events_watcher = None
        self.core_api = core_api
        self.event_queues_per_pod = {}
        self.pod_object_events_log = PodObjectEventsLog(self.event_queues_per_pod, callbacks)
        self.pod_kube_events_log = PodKubeEventsLog(self.event_queues_per_pod, callbacks)
        self.running = False
        self.thread = None

    async def _watch_pod_kube_events(self):
        self.pod_kube_events_watcher = kubernetes.watch.Watch()
        # TODO use list_event_for_all_namespaces?
        # TODO use field_selector to filter by namespace and involved object/kind==Pod?
        start_time = time.time()
        stream = self.pod_kube_events_watcher.stream(
            self.core_api.list_namespaced_event,
            DATA_FEED_NAMESPACE,
            watch=True,
            timeout_seconds=0
        )

        for message in stream:
            if not self.running:
                break
            raw_event = PodKubeRawEvent(message)
            # drop stale event
            delta = start_time - raw_event.object_last_timestamp.timestamp()
            if delta > 5:
                print(f'Dropped stale event: {delta}s')
                continue
            self.pod_kube_events_log.update_state(raw_event)
            await asyncio.sleep(0)

    async def _watch_pod_object_events(self):
        self.pod_object_events_watcher = kubernetes.watch.Watch()
        stream = self.pod_object_events_watcher.stream(
            self.core_api.list_pod_for_all_namespaces,
            watch=True,
            field_selector=f'metadata.namespace={DATA_FEED_NAMESPACE}',
            timeout_seconds=0
        )

        for message in stream:
            if not self.running:
                break
            raw_event = PodObjectRawEvent(message)
            # TODO use startTime to drop stale events
            self.pod_object_events_log.update_state(raw_event)
            await asyncio.sleep(0)

    async def _watch_events(self):
        return await asyncio.gather(*[self._watch_pod_kube_events(), self._watch_pod_object_events()])

    def _start_loop(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._watch_events())

    def start(self):
        if self.running:
            return
        print(f'KubeWatcher started')
        self.running = True
        self.thread = threading.Thread(target=self._start_loop)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        # TODO finish/cancel running tasks in asyncio loop and close loop
        if self.pod_kube_events_watcher:
            self.pod_kube_events_watcher.stop()
            self.pod_kube_events_watcher = None

        if self.pod_object_events_watcher:
            self.pod_object_events_watcher.stop()
            self.pod_object_events_watcher = None

        if self.thread:
            self.thread.join()
            self.thread = None
        print(f'KubeWatcher stopped')
