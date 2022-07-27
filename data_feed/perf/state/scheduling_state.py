import threading
import concurrent.futures

from perf.defines import DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER
from perf.state.phase_result_scheduling_state import PhaseResultSchedulingState
from perf.utils import local_now

MAX_RESCHEDULES = 1


class SchedulingState(PhaseResultSchedulingState):
    def __init__(self):
        super(SchedulingState, self).__init__()
        self.pods_work_queue = None
        self.pods_done = []
        self.pods_per_node = {}
        # contains info about oom_score_adj per pid per container per pod. See OOMHandler
        self.pids_per_container_per_pod = {}
        self.pods_priorities = {}
        self.reschedule_events_per_pod = {}
        self.last_oom_event_time_per_node = {}

        # TODO is this needed?
        self.global_lock = threading.Lock()

    def init_pods_work_queue(self, work_queue):
        self.pods_work_queue = work_queue

    def get_last_scheduled_pod(self, node):
        if node not in self.pods_per_node or len(self.pods_per_node[node]) == 0:
            return None
        return self.pods_per_node[node][-1]

    def get_node_for_scheduled_pod(self, pod):
        for node in self.pods_per_node:
            for scheduled_pod in self.pods_per_node[node]:
                if scheduled_pod == pod:
                    return node
        return None

    def get_containers_per_pod(self, pod):
        # TODO make this dynamic
        return [DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER]

    def get_schedulable_pod_priority(self, node_name):
        last_pod = self.get_last_scheduled_pod(node_name)
        if last_pod is None:
            priority = 10000
        else:
            # TODO what if key does not exist
            last_priority = self.pods_priorities[last_pod]
            priority = last_priority - 1
        return priority

    def add_pod_to_schedule_state(self, pod_name, node_name, priority):
        # check all nodes to make sure pod is not scheduled twice
        for node in self.pods_per_node:
            if pod_name in self.pods_per_node[node]:
                raise Exception(f'[Scheduler] Pod {pod_name} is already assigned to node {node}')

        # scheduling state update
        if node_name in self.pods_per_node:
            self.pods_per_node[node_name].append(pod_name)
        else:
            self.pods_per_node[node_name] = [pod_name]

        self.pods_priorities[pod_name] = priority

    def remove_pod_from_schedule_state(self, pod_name):
        node_name = None
        count = 0  # to make sure only 1 pod exists
        for node in self.pods_per_node:
            if pod_name in self.pods_per_node[node]:
                count += 1
                node_name = node
        if node_name is None:
            return
        if count > 1:
            raise Exception(f'[Scheduler] Found {count} pods with name {pod_name}, should be 1')
        self.pods_per_node[node_name].remove(pod_name)

        # clean priority
        del self.pods_priorities[pod_name]

    def pop_or_wait_work_queue(self, pending_futures):
        pod_name = None
        if len(self.pods_work_queue) == 0:
            # check running tasks
            # wait for first finished task
            print(f'[Scheduler] No pods in queue, waiting for pending futures to finish...')
            for _ in concurrent.futures.as_completed(pending_futures.keys()):
                self.global_lock.acquire()
                # check if it was the last one
                all_done = True
                for f in pending_futures.keys():
                    if not f.done():
                        all_done = False
                if len(self.pods_work_queue) == 0:
                    if all_done:
                        # all tasks finished and no more queued
                        self.global_lock.release()
                        print(f'[Scheduler] All tasks finished')
                        return None
                    else:
                        # continue waiting
                        print(f'[Scheduler] Continue waiting')
                        self.global_lock.release()
                        continue
                else:
                    # continue scheduling
                    pod_name = self.pods_work_queue.pop()
                    print(f'[Scheduler] Continue scheduling with {pod_name}')
                    break
        else:
            pod_name = self.pods_work_queue.pop()
            print(f'[Scheduler] Popped {pod_name}')

        if self.global_lock.locked():
            self.global_lock.release()

        return pod_name

    def reschedule_or_complete(self, pod_name, reschedule, reason):
        self.remove_pod_from_schedule_state(pod_name)
        # decide if move to done schedule state or reschedule for another run
        self.global_lock.acquire()
        if not reschedule:
            print(f'[Scheduler] {pod_name} done, {reason}')
            self.pods_done.append(pod_name)
        else:
            reschedule_counter = len(self.get_reschedule_reasons(pod_name))
            if reschedule_counter < MAX_RESCHEDULES:
                # reschedule - append to the end of the work queue
                print(f'[Scheduler] {pod_name} rescheduled, reason {reason}')
                self.inc_reschedule_counter(pod_name, reason)
                self.pods_work_queue.append(pod_name)
            else:
                print(f'[Scheduler] {pod_name} done after max {MAX_RESCHEDULES} reschedule attempts')
                self.pods_done.append(pod_name)

        self.global_lock.release()
        # TODO handle
        # exception calling callback for <Future at 0x110fa6760 state=finished returned tuple>
        # Traceback (most recent call last):
        #   File "/usr/local/Cellar/python@3.9/3.9.12/Frameworks/Python.framework/Versions/3.9/lib/python3.9/concurrent/futures/_base.py", line 330, in _invoke_callbacks
        #     callback(self)
        #   File "/Users/anov/IdeaProjects/svoe/data_feed/perf/scheduler/scheduler.py", line 305, in done_estimation_callback
        #     self.scheduling_state.reschedule_or_complete(pod_name, reschedule, reason)
        #   File "/Users/anov/IdeaProjects/svoe/data_feed/perf/state/scheduling_state.py", line 141, in reschedule_or_complete
        #     self.global_lock.release()
        # RuntimeError: release unlocked lock

    def get_reschedule_reasons(self, pod_name):
        if pod_name not in self.reschedule_events_per_pod:
            return []
        return self.reschedule_events_per_pod[pod_name]

    def inc_reschedule_counter(self, pod_name, reason):
        if pod_name not in self.reschedule_events_per_pod:
            self.reschedule_events_per_pod[pod_name] = []
        self.reschedule_events_per_pod[pod_name].append(reason)

    def find_pod_container_by_pid(self, pid):
        for pod in self.pids_per_container_per_pod:
            for container in self.pids_per_container_per_pod[pod]:
                if pid in self.pids_per_container_per_pod[pod][container]:
                    return pod, container
        return None, None

    def get_last_oom_time(self, node):
        if node not in self.last_oom_event_time_per_node:
            return None
        return self.last_oom_event_time_per_node[node]

    def mark_last_oom_time(self, node):
        self.last_oom_event_time_per_node[node] = local_now()
