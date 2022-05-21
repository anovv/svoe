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

    async def _watch_pod_kube_events(self):
        self.pod_kube_events_watcher = kubernetes.watch.Watch()
        # TODO use list_event_for_all_namespaces?
        # TODO use field_selector to filter by namespace and involved object/kind==Pod?
        # TODO timeout_seconds=0
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
            delta = time.time() - raw_event.object_last_timestamp.timestamp()
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

    def start(self, loop):
        self.running = True
        # loop.create_task(self._watch_pod_kube_events())
        loop.create_task(self._watch_pod_object_events())

    def stop(self):
        self.running = False
        # TODO finish/cancel running tasks in asyncio loop and close loop
        if self.pod_kube_events_watcher:
            self.pod_kube_events_watcher.stop()
            self.pod_kube_events_watcher = None

        if self.pod_object_events_watcher:
            self.pod_object_events_watcher.stop()
            self.pod_object_events_watcher = None
            print('Stopped watcher')


    # @staticmethod
    # def _get_container_state(pod_status):
    #     container_status = next(filter(lambda c: c.name == DATA_FEED_CONTAINER, pod_status.container_statuses), None)
    #     state = container_status.state
    #     if state.running:
    #         return 'running', state.running
    #     if state.terminated:
    #         return 'terminated', state.terminated # state.terminated.reason == "Completed"
    #     if state.waiting:
    #         return 'waiting', state.waiting
    #
    # @staticmethod
    # def wait_for_pod_to_run_for(pod_name, run_for_s):
    #     # TODO check status here and early exit if failure?
    #     print(f'Started running pod {pod_name} for {run_for_s}s...')
    #     # for easier interrupts use for loop with short sleeps
    #     start = time.time()
    #     for i in range(int(run_for_s)):
    #         if i%5 == 0:
    #             print(f'Running pod {pod_name}: {run_for_s - (time.time() - start)}s left')
    #         time.sleep(1)
    #
    #     print(f'Done running pod {pod_name} to finish')
    #
    # def wait_for_pod_to(self, pod_name, appear, timeout):
    #     print(f'Waiting for pod {pod_name} to {"appear" if appear else "disappear"}...')
    #     start = time.time()
    #     while time.time() - start < timeout:
    #         try:
    #             self.core_api.read_namespaced_pod(pod_name, DATA_FEED_NAMESPACE)
    #             if appear:
    #                 print(f'Pod {pod_name} appeared')
    #                 return True
    #         except:
    #             if not appear:
    #                 print(f'Pod {pod_name} disappeared')
    #                 return True
    #             pass
    #         time.sleep(1)
    #
    #     print(f'Timeout waiting for pod {pod_name} to {"appear" if appear else "disappear"}')
    #     return False
    #
    # def wait_for_pod_to_start_running(self, pod_name, timeout):
    #     # TODO long timeout only on image pull (PodInitializing status)?
    #     # image pull may take up to 20 mins
    #     # TODO need to check health endpoint
    #     # TODO use Watch and events api
    #     # https://www.programcreek.com/python/example/111707/kubernetes.watch.Watch Example 3
    #     # https://docs.bitnami.com/tutorials/kubernetes-async-watches
    #     # https://shipit.dev/posts/k8s-operators-with-python-part-1.html
    #
    #     print(f'Waiting for pod {pod_name} to start running...')
    #     start = time.time()
    #     count = 0
    #     while time.time() - start < timeout:
    #         pod = self.core_api.read_namespaced_pod(pod_name, DATA_FEED_NAMESPACE)
    #         # check pod.status.conditions
    #         pod_status_phase = pod.status.phase # Pending, Running, Succeeded, Failed, Unknown
    #         container_state, _ = self._get_container_state(pod.status) # running, terminated, waiting
    #         if pod_status_phase == 'Running' and container_state == 'running':
    #             print(f'Pod {pod_name}: {pod_status_phase}, Container: {container_state}')
    #             return True
    #         if pod_status_phase == 'Failed':
    #             print(f'Pod {pod_name}: {pod_status_phase}, Container: {container_state}')
    #             return False
    #         if count%5 == 0:
    #             print(f'Waiting for pod {pod_name} to start running, {timeout - (time.time() - start)}s left , pod: {pod_status_phase}, container: {container_state}')
    #         count += 1
    #         time.sleep(1)
    #
    #     print(f'Timeout waiting for pod {pod_name} to start running')
    #     return False
