import time

import ray

# from data_catalog.indexer.actors.coordinator import Coordinator
# from data_catalog.indexer.actors.db import DbReader, DbWriter, DbActor
# from data_catalog.indexer.actors.queues import DownloadQueue, StoreQueue, InputQueue
from data_catalog.indexer.actors.db import DbActor

# for pipelined queue https://docs.ray.io/en/latest/ray-core/patterns/pipelining.html
# for backpressure https://docs.ray.io/en/latest/ray-core/patterns/limit-pending-tasks.html
# fro mem usage https://docs.ray.io/en/releases-1.12.0/ray-core/objects/memory-management.html
# memory monitor https://docs.ray.io/en/latest/ray-core/scheduling/ray-oom-prevention.html

# for memory profiling https://discuss.ray.io/t/unexplained-memory-usage-with-cloudpickle-obj-store/6877
# and https://github.com/cadedaniel/cadelabs/blob/master/stackoverflow/72970940/script.py

# implement workflows (for checkpointing/persistence):
# https://docs.ray.io/en/latest/workflows/key-concepts.html
from data_catalog.indexer.actors.scheduler import Scheduler
from data_catalog.indexer.actors.stats import Stats
from data_catalog.indexer.models import InputItemBatch

INPUT_ITEM_BATCH_SIZE = 2
WRITE_INDEX_ITEM_BATCH_SIZE = 20


class Indexer:
    stats: Stats
    db_actor: DbActor
    scheduler: Scheduler

    def run(self):
        # run stats
        self.stats = Stats.remote()
        self.stats.run.remote()

        # TODO make this an actor pool
        # db actor
        self.db_actor = DbActor.remote()

        # run scheduler
        self.scheduler = Scheduler.remote(self.stats, self.db_actor)
        self.scheduler.run.remote()

    def pipe_input(self, input_batch: InputItemBatch):
        # TODO do we need ray.get here?
        ray.get(self.scheduler.pipe_input.remote(input_batch))


