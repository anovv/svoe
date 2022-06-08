
class SchedulingState:
    def __init__(self):
        self.pods_work_queue = None
        self.pods_done = []
        self.pods_per_node = {}
        self.pods_priorities = {}

    def init_pods_work_queue(self, work_queue):
        self.pods_work_queue = work_queue

    def get_last_scheduled_pod(self, node):
        if node not in self.pods_per_node or len(self.pods_per_node[node]) == 0:
            return None
        return self.pods_per_node[node][-1]

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
