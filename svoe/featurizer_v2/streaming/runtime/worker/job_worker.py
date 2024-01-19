import ray

from svoe.featurizer_v2.streaming.runtime.core.execution_graph.execution_graph import ExecutionVertex


@ray.remote
class JobWorker:

    def __init__(self, execution_vertex: ExecutionVertex):
        self.execution_vertex = execution_vertex