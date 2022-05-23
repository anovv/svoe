import datetime
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
        self.pod_object_events_thread = None
        self.pod_object_events_log = PodObjectEventsLog(self.event_queues_per_pod, callbacks)
        self.pod_kube_events_thread = None
        self.pod_kube_events_log = PodKubeEventsLog(self.event_queues_per_pod, callbacks)
        self.running = False

    def _watch_pod_kube_events_blocking(self):
        self.pod_kube_events_watcher = kubernetes.watch.Watch()
        start_time = time.time()
        stream = self.pod_kube_events_watcher.stream(
            self.core_api.list_event_for_all_namespaces,
            watch=True,
            field_selector=f'metadata.namespace={DATA_FEED_NAMESPACE}',
            timeout_seconds=0
        )

        for message in stream:
            if not self.running:
                break
            raw_event = PodKubeRawEvent(message)
            # drop stale event
            delta = start_time - raw_event.object_last_timestamp.timestamp()
            if delta > 5:
                continue

            # TODO
            # now = datetime.datetime.now()
            # ts = raw_event.object_last_timestamp
            # print(f'{now}, {ts}, {raw_event.object_reason}, {raw_event.involved_object_field_path}')

            self.pod_kube_events_log.update_state(raw_event)

    def watch_pod_kube_events(self):
        self.pod_kube_events_thread = threading.Thread(target=self._watch_pod_kube_events_blocking)
        self.pod_kube_events_thread.start()

    def _watch_pod_object_events_blocking(self):
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

    def watch_pod_object_events(self):
        self.pod_object_events_thread = threading.Thread(target=self._watch_pod_object_events_blocking)
        self.pod_object_events_thread.start()

    # async def _watch_events(self):
    #     return
        # return await asyncio.gather(*[self._watch_pod_kube_events(), self._watch_pod_object_events()])

    # def _start_loop(self):
    #     loop = asyncio.new_event_loop()
    #     loop.run_until_complete(self._watch_events())

    def start(self):
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
        if self.pod_kube_events_watcher:
            self.pod_kube_events_watcher.stop()
            self.pod_kube_events_watcher = None

        if self.pod_object_events_watcher:
            self.pod_object_events_watcher.stop()
            self.pod_object_events_watcher = None

        if self.pod_object_events_thread:
            self.pod_object_events_thread.join()
            self.pod_object_events_thread = None

        if self.pod_kube_events_thread:
            self.pod_kube_events_thread.join()
            self.pod_kube_events_thread = None
        print(f'KubeWatcher stopped')
