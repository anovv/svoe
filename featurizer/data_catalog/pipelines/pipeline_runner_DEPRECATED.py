import ray
from featurizer.data_catalog.common.actors.db import DbActor

# for pipelined queue https://docs.ray.io/en/latest/ray-core/patterns/pipelining.html
# for backpressure https://docs.ray.io/en/latest/ray-core/patterns/limit-pending-tasks.html
# fro mem usage https://docs.ray.io/en/releases-1.12.0/ray-core/objects/memory-management.html
# memory monitor https://docs.ray.io/en/latest/ray-core/scheduling/ray-oom-prevention.html

# for memory profiling https://discuss.ray.io/t/unexplained-memory-usage-with-cloudpickle-obj-store/6877
# and https://github.com/cadedaniel/cadelabs/blob/master/stackoverflow/72970940/script.py

# implement workflows (for checkpointing/persistence):
# https://docs.ray.io/en/latest/workflows/key-concepts.html
from featurizer.data_catalog.common.actors.scheduler_DEPRECATED import Scheduler
from featurizer.data_catalog.common.data_models.models import InputItemBatch

# TODO workflow exception handling
#  example exceptions
#  download_task: botocore.exceptions.ReadTimeoutError: Read timeout on endpoint URL: "None"
# from data_catalog.pipelines.dag import Dag


class PipelineRunner:
    db_actor: DbActor
    scheduler: Scheduler

    def run(self, dag):
        # TODO init throughput

        # TODO use named actors and with get_if_exists: a = Greeter.options(name="g1", get_if_exists=True)
        # TODO uncomment when Stats refactoring is done
        # run stats
        # self.stats = Stats.remote()
        # self.stats.run.remote()

        # TODO make db an actor pool if lots of connections
        # db actor
        self.db_actor = DbActor.remote()

        # run scheduler
        self.scheduler = Scheduler.remote(self.db_actor)
        self.scheduler.run.remote(dag)
        print('PipelineRunner started')

    def wait_to_finish(self):
        ray.get(self.scheduler.stop.remote())

    def pipe_input(self, input_batch: InputItemBatch):
        # TODO make it async? do we need ray.get here?
        ray.get(self.scheduler.pipe_input.remote(input_batch))


