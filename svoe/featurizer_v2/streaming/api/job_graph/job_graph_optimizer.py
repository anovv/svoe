from svoe.featurizer_v2.streaming.api.job_graph.job_graph import JobGraph


class JobGraphOptimizer:

    def __init__(self, job_graph: JobGraph):
        self.job_graph = job_graph

    def optimize(self) -> JobGraph:
        # TODO implement optimizations
        return self.job_graph