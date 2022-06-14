import threading
import concurrent.futures

from perf.state.phase_result_scheduling_state import PhaseResultSchedulingState

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
        self.reschedule_counters_per_pod = {}

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

        raise ValueError(f'Pod {pod} is not scheduled on any node')

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
                raise Exception(f'Pod {pod_name} is already assigned to node {node}')

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
        if node_name is None or count > 1:
            raise Exception(f'Found {count} pods with name {pod_name}, should be 1')
        self.pods_per_node[node_name].remove(pod_name)

        # clean priority
        del self.pods_priorities[pod_name]

    def pop_or_wait_work_queue(self, pending_futures):
        pod_name = None
        if len(self.pods_work_queue) == 0:
            # check running tasks
            # wait for first finished task
            print(f'No pods in queue, waiting for pending futures to finish')
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
                        print(f'All tasks finished')
                        return None
                    else:
                        # continue waiting
                        print(f'Continue waiting')
                        self.global_lock.release()
                        continue
                else:
                    # continue scheduling
                    pod_name = self.pods_work_queue.pop()
                    print(f'Continue scheduling with {pod_name}')
                    break
        else:
            pod_name = self.pods_work_queue.pop()
            print(f'Popped {pod_name}')

        if self.global_lock.locked():
            self.global_lock.release()

        return pod_name

    def reschedule_or_complete(self, pod_name, success):
        self.remove_pod_from_schedule_state(pod_name)
        # decide if move to done schedule state or reschedule for another run
        # TODO add reschedule reason?
        self.global_lock.acquire()
        if success:
            # success
            print(f'Pod {pod_name} done')
            self.pods_done.append(pod_name)
        else:
            reschedule_counter = self.get_reschedule_counter(pod_name)
            if reschedule_counter < MAX_RESCHEDULES:
                # reschedule - append to the end of the work queue
                print(f'Pod {pod_name} rescheduled')
                self.set_reschedule_counter(pod_name, reschedule_counter + 1)
                self.pods_work_queue.append(pod_name)
            else:
                print(f'Pod {pod_name} done after {reschedule_counter} reschedules')
                self.pods_done.append(pod_name)

        self.global_lock.release()

    def get_reschedule_counter(self, pod_name):
        if pod_name not in self.reschedule_counters_per_pod:
            return 0
        return self.reschedule_counters_per_pod[pod_name]

    def set_reschedule_counter(self, pod_name, counter):
        self.reschedule_counters_per_pod[pod_name] = counter