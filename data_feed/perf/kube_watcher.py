from defines import *
import time
import json
import kubernetes


class KubeWatcher:
    def __init__(self, core_api):
        self.watcher = None
        self.core_api = core_api

    @staticmethod
    def _get_container_state(pod_status):
        container_status = next(filter(lambda c: c.name == DATA_FEED_CONTAINER, pod_status.container_statuses), None)
        state = container_status.state
        if state.running:
            return 'running', state.running
        if state.terminated:
            return 'terminated', state.terminated # state.terminated.reason == "Completed"
        if state.waiting:
            return 'waiting', state.waiting

    @staticmethod
    def wait_for_pod_to_run_for(self, pod_name, run_for_s):
        # TODO check status here and early exit if failure?
        print(f'Started running pod {pod_name} for {run_for_s}s...')
        # for easier interrupts use for loop with short sleeps
        start = time.time()
        for i in range(int(run_for_s)):
            if i%5 == 0:
                print(f'Running pod {pod_name}: {run_for_s - (time.time() - start)}s left')
            time.sleep(1)

        print(f'Done running pod {pod_name} to finish')

    def wait_for_pod_to(self, pod_name, appear, timeout):
        print(f'Waiting for pod {pod_name} to {"appear" if appear else "disappear"}...')
        start = time.time()
        while time.time() - start < timeout:
            try:
                self.core_api.read_namespaced_pod(pod_name, DATA_FEED_NAMESPACE)
                if appear:
                    print(f'Pod {pod_name} appeared')
                    return True
            except:
                if not appear:
                    print(f'Pod {pod_name} disappeared')
                    return True
                pass
            time.sleep(1)

        print(f'Timeout waiting for pod {pod_name} to {"appear" if appear else "disappear"}')
        return False

    def wait_for_pod_to_start_running(self, pod_name, timeout):
        # TODO long timeout only on image pull (PodInitializing status)?
        # image pull may take up to 20 mins
        # TODO need to check health endpoint
        # TODO use Watch and events api
        # https://www.programcreek.com/python/example/111707/kubernetes.watch.Watch Example 3
        # https://docs.bitnami.com/tutorials/kubernetes-async-watches
        # https://shipit.dev/posts/k8s-operators-with-python-part-1.html

        print(f'Waiting for pod {pod_name} to start running...')
        start = time.time()
        count = 0
        while time.time() - start < timeout:
            pod = self.core_api.read_namespaced_pod(pod_name, DATA_FEED_NAMESPACE)
            # check pod.status.conditions
            pod_status_phase = pod.status.phase # Pending, Running, Succeeded, Failed, Unknown
            container_state, _ = self._get_container_state(pod.status) # running, terminated, waiting
            if pod_status_phase == 'Running' and container_state == 'running':
                print(f'Pod {pod_name}: {pod_status_phase}, Container: {container_state}')
                return True
            if pod_status_phase == 'Failed':
                print(f'Pod {pod_name}: {pod_status_phase}, Container: {container_state}')
                return False
            if count%5 == 0:
                print(f'Waiting for pod {pod_name} to start running, {timeout - (time.time() - start)}s left , pod: {pod_status_phase}, container: {container_state}')
            count += 1
            time.sleep(1)

        print(f'Timeout waiting for pod {pod_name} to start running')
        return False

    def watch_namespaced_events(self):
        self.watcher = kubernetes.watch.Watch()
        stream = watcher.stream(self.core_api.list_namespaced_event, DATA_FEED_NAMESPACE, timeout_seconds=60*60)
        for raw_event in stream:
            filtered = {
                # ADDED, MODIFIED (Unhealthy: object.count, BackOff: object.count)
                'type': raw_event['type'],
                # Event
                'object.kind': raw_event['object'].kind,
                # Normal, Warning
                'object.type': raw_event['object'].type,
                # Normal:
                #   StatefulSet:
                #     SuccessfulCreate: "create Pod {name} in StatefulSet {name} successful"
                #     SuccessfulDelete: "delete Pod data-feed-binance-spot-eb540d90be-ss-0 in StatefulSet data-feed-binance-spot-eb540d90be-ss successful"
                #   Pod:
                #     Scheduled: "Successfully assigned data-feed/data-feed-binance-spot-eb540d90be-ss-0 to minikube-1-m02
                #     per container:
                #       Pulled: "Container image \"redis:alpine\" already present on machine"
                #       Created: "Created container redis"
                #       Started: "Started container redis"
                #       Pulling: "Pulling image \"oliver006/redis_exporter:latest\""
                #       Killing: "Stopping container redis"
                #       BackOff:  "Back-off restarting failed container"
                # Warning:
                #   Pod:
                #     per container:
                #       Unhealthy:  "Liveness probe failed: Get \"http://10.244.1.38:1234/health\": context deadline exceeded (Client.Timeout exceeded while awaiting headers)"
                #       or "Startup probe failed: HTTP probe failed with statuscode: 500"
                'object.reason': raw_event['object'].reason,
                'object.message': raw_event['object'].message,
                # Pod and StatefulSet
                'object.count': raw_event['object'].count,
                # null
                'object.action': raw_event['object'].action,
                # Pod, StatefulSet
                'object.involved_object.kind': raw_event['object'].involved_object.kind,
                # pod or ss name
                'object.involved_object.name': raw_event['object'].involved_object.name,
                # StatefulSet: no field,
                # Pod: spec.containers{container_name} for Pulled, Created, Started, Pulling, Unhealthy, Killing
                'object.involved_object.field_path': raw_event['object'].involved_object.field_path,
                'object.first_timestamp': raw_event['object'].first_timestamp,
                'object.last_timestamp': raw_event['object'].last_timestamp,
            }
            print('---------------------')
            print(json.dumps(filtered, indent = 4, default=str))
            # print(json.dumps(raw_event.raw_object, indent = 4))
        print('Done')

    def stop_watcher(self):
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
            print('Stopped watcher')

    def watch_pod_events(self, pod_name):
        global watcher
        watcher = kubernetes.watch.Watch()
        # TODO timeout ?
        stream = watcher.stream(self.core_api.list_namespaced_pod, namespace=DATA_FEED_NAMESPACE) #field_selector=f'metadata.name=[{pod_name}]')
        for raw_event in stream:
            # TODO jsondiff
            # https://github.com/xlwings/jsondiff
            status = raw_event['raw_object']['status']
            status_filtered = {}
            if 'phase' in status:
                status_filtered['phase'] = raw_event['raw_object']['status']['phase']
            if 'conditions' in status:
                status_filtered['conditions'] = raw_event['raw_object']['status']['conditions']
            if 'containerStatuses' in status:
                status_filtered['containerStatuses'] = raw_event['raw_object']['status']['containerStatuses']

            filtered = {
                'type': raw_event['type'],
                'name': raw_event['raw_object']['metadata']['name'],
                # 'diff_status': jsondiff.diff(last_status, status_filtered, marshal=True)
                'status': status_filtered,
                # TODO timestamp
                # 'first_timestamp': raw_event['first_timestamp'],
                # 'last_timestamp': raw_event['last_timestamp'],
            }
            print('---------------------')
            print(json.dumps(filtered, indent=4, default=str))
