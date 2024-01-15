import enum
from typing import List, Dict

from svoe.featurizer_v2.streaming.api.operator.operator import StreamOperator
from svoe.featurizer_v2.streaming.api.partition.partition import Partition


class JobEdge:
    def __init__(
        self,
        source_vertex_id: int,
        target_vertex_id: int,
        partition: Partition,
    ):
        self.source_vertex_id = source_vertex_id
        self.target_vertex_id = target_vertex_id

        # TODO is this ok
        self.source_operator_id = source_vertex_id
        self.target_operator_id = target_vertex_id

        self.partition = partition


class VertexType(enum.Enum):
    SOURCE = 0  # data reader, 0 input, 1 output
    PROCESS = 1  # 1 input, 1 output
    SINK = 2  # data writer, 1 input, 0 output
    UNION = 3  # simply group all input elements, 2 inputs, 1 output,
    JOIN = 4  # group input elements with a specified method, 2 inputs, 1 output


class JobVertex:

    def __init__(
        self,
        vertex_id: int,
        parallelism: int,
        vertex_type: VertexType,
        stream_operator: StreamOperator,
    ):
        self.vertex_id = vertex_id
        self.parallelism = parallelism
        self.vertex_type = vertex_type
        self.stream_operator = stream_operator

        # set operator id
        self.stream_operator.id = vertex_id


class JobGraph:
    def __init__(
        self,
        job_name: str,
        job_config: Dict
    ):
        self.job_name = job_name
        self.job_config = job_config
        self.job_vertices: List[JobVertex] = []
        self.job_edges: List[JobEdge] = []

    def add_vertex(self, job_vertex: JobVertex):
        self.job_vertices.append(job_vertex)

    def add_edge_if_not_exists(self, job_edge: JobEdge):
        for edge in self.job_edges:
            if edge.source_vertex_id == job_edge.source_vertex_id and \
                    edge.target_vertex_id == job_edge.target_vertex_id:
                return
        self.job_edges.append(job_edge)
