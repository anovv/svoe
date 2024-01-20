import logging
import time
from random import randint
from typing import Dict

import ray
from ray.actor import ActorHandle

from svoe.featurizer_v2.streaming.runtime.core.execution_graph.execution_graph import ExecutionGraph
from svoe.featurizer_v2.streaming.runtime.transfer.channel import Channel
from svoe.featurizer_v2.streaming.runtime.worker.job_worker import JobWorker

from ray._private.state import actors

VALID_PORT_RANGE = (30000, 65000)


logger = logging.getLogger(__name__)

class WorkerNetworkInfo:

    def __init__(self, node_ip: str, node_id: str, data_writer_port: int):
        self.node_ip = node_ip
        self.node_id = node_id
        self.data_writer_port = data_writer_port


class WorkerLifecycleCoordinator:

    def __init__(self):
        self._used_ports = {}

    def create_workers(self, num_workers) -> Dict[ActorHandle, WorkerNetworkInfo]:
        workers = []
        for _ in range(num_workers):
            workers.append(JobWorker.remote())

        workers_info = {}
        all_actors_info = actors()
        for w in workers:
            for info in all_actors_info:
                if w._actor_id() == info['ActorID']:
                    workers_info[w] = info

        assert len(workers_info) == num_workers

        res = {}
        for w in workers_info:
            node_id = workers_info[w]['Address']['NodeID']
            node_ip = workers_info[w]['Address']['IPAddress']
            res[w] = WorkerNetworkInfo(
                node_ip=node_ip,
                node_id=node_id,
                data_writer_port=self._gen_port(node_id)
            )

        logger.info(f'Created {num_workers} workers')

        return res

    # construct channels based on Ray assigned actor IPs and update execution_graph
    def init_workers_and_update_graph_channels(
        self,
        workers_info: Dict[ActorHandle, WorkerNetworkInfo],
        execution_graph: ExecutionGraph
    ):
        assert len(workers_info) == len(execution_graph.execution_vertices_by_id)
        # map workers to vertices
        vertex_id_to_worker = dict(zip(execution_graph.execution_vertices_by_id.keys(), workers_info.keys()))

        # create channels
        for edge in execution_graph.execution_edges:
            source_worker = vertex_id_to_worker[edge.source_execution_vertex.execution_vertex_id]

            source_ip = workers_info[source_worker].node_ip
            source_port = workers_info[source_worker].data_writer_port

            channel = Channel(
                channel_id=edge.id,
                source_ip=source_ip,
                source_port=source_port
            )

            edge.set_channel(channel)

        # init workers
        f = []
        for vertex_id, worker in vertex_id_to_worker:
            execution_vertex = execution_graph.execution_vertices_by_id[vertex_id]
            f.append(worker.init.remote(execution_vertex))

        t = time.time()
        ray.wait(f)

        logger.info(f'Inited {len(vertex_id_to_worker)} workers in {time.time() - t}s')

    def _gen_port(self, node_id) -> int:
        while True:
            port = randint(VALID_PORT_RANGE[0], VALID_PORT_RANGE[1])
            if node_id not in self._used_ports:
                self._used_ports[node_id] = [port]
                break
            else:
                if len(self._used_ports[node_id]) == VALID_PORT_RANGE[1] - VALID_PORT_RANGE[0]:
                    raise RuntimeError('Too many open ports')
                if port not in self._used_ports[node_id]:
                    self._used_ports[node_id].append(port)
                    break

        return port


