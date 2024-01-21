import logging
import time
from random import randint
from typing import Dict, List

import ray
from ray.actor import ActorHandle

from svoe.featurizer_v2.streaming.runtime.core.execution_graph.execution_graph import ExecutionGraph, ExecutionVertex
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


class WorkerLifecycleController:

    def __init__(self):
        self._used_ports = {}

    def create_dummy_workers(self, execution_graph: ExecutionGraph) -> Dict[ActorHandle, WorkerNetworkInfo]:
        workers = []
        logger.info(f'Creating {len(execution_graph.execution_vertices_by_id)} workers...')
        for vertex in execution_graph.execution_vertices_by_id.values():
            resources = vertex.resources
            options_kwargs = {
                'max_restarts': -1
            }
            if resources.num_cpus is not None:
                options_kwargs['num_cpus'] = resources.num_cpus
            if resources.num_gpus is not None:
                options_kwargs['num_gpus'] = resources.num_gpus
            if resources.memory is not None:
                options_kwargs['memory'] = resources.memory
            worker = JobWorker.remote(**options_kwargs)
            workers.append(worker)
            vertex.set_worker(worker)

        workers_info = {}
        all_actors_info = actors()
        for w in workers:
            for info in all_actors_info:
                if w._actor_id() == info['ActorID']:
                    workers_info[w] = info

        assert len(workers_info) == len(workers)

        res = {}
        for w in workers_info:
            node_id = workers_info[w]['Address']['NodeID']
            node_ip = workers_info[w]['Address']['IPAddress']
            res[w] = WorkerNetworkInfo(
                node_ip=node_ip,
                node_id=node_id,
                data_writer_port=self._gen_port(node_id)
            )

        logger.info(f'Created {len(workers)} workers')

        return res

    # construct channels based on Ray assigned actor IPs and update execution_graph
    def init_workers_and_update_graph_channels(
        self,
        workers_info: Dict[ActorHandle, WorkerNetworkInfo],
        execution_graph: ExecutionGraph
    ):
        logger.info(f'Initializing {len(execution_graph.execution_vertices_by_id)} workers...')
        assert len(workers_info) == len(execution_graph.execution_vertices_by_id)

        # create channels
        for edge in execution_graph.execution_edges:
            source_worker = edge.source_execution_vertex.worker

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
        for execution_vertex in execution_graph.execution_vertices_by_id.values():
            worker = execution_vertex.worker
            f.append(worker.init.remote(execution_vertex))

        t = time.time()
        ray.wait(f)
        logger.info(f'Inited workers in {time.time() - t}s')

    def start_workers(self, execution_graph: ExecutionGraph):
        logger.info(f'Starting workers...')
        # start source workers first
        f = []
        for w in execution_graph.get_source_workers():
            f.append(w.start_or_rollback.remote())

        t = time.time()
        ray.wait(f)
        logger.info(f'Started source workers in {time.time() - t}s')

        # start rest
        f = []
        for w in execution_graph.get_non_source_workers():
            f.append(w.start_or_rollback.remote())

        t = time.time()
        ray.wait(f)
        logger.info(f'Started non-source workers in {time.time() - t}s')

    def delete_workers(self, vertices: List[ExecutionVertex]):
        # TODO
        raise NotImplementedError

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


