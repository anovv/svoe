import ray
from data_catalog.common.actors.db import DbActor

# for pipelined queue https://docs.ray.io/en/latest/ray-core/patterns/pipelining.html
# for backpressure https://docs.ray.io/en/latest/ray-core/patterns/limit-pending-tasks.html
# fro mem usage https://docs.ray.io/en/releases-1.12.0/ray-core/objects/memory-management.html
# memory monitor https://docs.ray.io/en/latest/ray-core/scheduling/ray-oom-prevention.html

# for memory profiling https://discuss.ray.io/t/unexplained-memory-usage-with-cloudpickle-obj-store/6877
# and https://github.com/cadedaniel/cadelabs/blob/master/stackoverflow/72970940/script.py

# implement workflows (for checkpointing/persistence):
# https://docs.ray.io/en/latest/workflows/key-concepts.html
from data_catalog.common.actors.scheduler import Scheduler
from data_catalog.common.actors.stats import Stats
from data_catalog.common.data_models.models import InputItemBatch

# TODO workflow exception handling
#  example exceptions
#  download_task: botocore.exceptions.ReadTimeoutError: Read timeout on endpoint URL: "None"
# from data_catalog.pipelines.dag import Dag


class PipelineRunner:
    stats: Stats
    db_actor: DbActor
    scheduler: Scheduler

    def run(self, dag):
        # TODO init throughput
        #  workflow.init(max_running_workflows=10, max_pending_workflows=50)

        # TODO for workflow stats (per task) - workflow metadata
        # https://docs.ray.io/en/latest/workflows/metadata.html
        # run stats
        self.stats = Stats.remote()
        self.stats.run.remote()

        # TODO make this an actor pool
        # db actor
        self.db_actor = DbActor.remote()

        # run scheduler
        self.scheduler = Scheduler.remote(self.stats, self.db_actor)
        self.scheduler.run.remote(dag)
        print('PipelineRunner started')

    def wait_to_finish(self):
        ray.get(self.scheduler.stop.remote())

    def pipe_input(self, input_batch: InputItemBatch):
        # TODO make it async? do we need ray.get here?
        ray.get(self.scheduler.pipe_input.remote(input_batch))


