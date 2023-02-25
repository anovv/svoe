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
    # input_queue: InputQueue
    # download_queue: DownloadQueue
    # store_queue: StoreQueue
    # coordintator: Coordinator
    stats: Stats
    db_actor: DbActor
    scheduler: Scheduler

    def run(self):
        # run stats
        self.stats = Stats.remote()
        self.stats.run.remote()

        # db actor
        self.db_actor = DbActor.remote()

        # run scheduler
        self.scheduler = Scheduler.remote(self.stats, self.db_actor)
        self.scheduler.run.remote()

        # # init queue actors
        # self.input_queue = InputQueue.remote()
        # self.download_queue = DownloadQueue.remote()
        # self.store_queue = StoreQueue.remote(WRITE_INDEX_ITEM_BATCH_SIZE)
        #
        # # init coordinator
        # self.coordintator = Coordinator.remote(self.stats, self.download_queue, self.store_queue)
        #
        # # init db actors
        # db_readers = [DbReader.remote(self.stats, self.input_queue, self.download_queue) for _ in range(num_db_readers)]
        # for r in db_readers:
        #     r.run.remote()
        # db_writers = [DbWriter.remote(self.stats, self.store_queue) for _ in range(num_db_writers)]
        # for w in db_writers:
        #     w.run.remote()
        # self.coordintator.run.remote()

    def pipe_input(self, input_batch: InputItemBatch):
        # TODO do we need ray.get here?
        ray.get(self.scheduler.pipe_input.remote(input_batch))

    # TODO add throughput limit, backpressure
    # for input_batch in generate_input_items(INPUT_ITEM_BATCH_SIZE):
    # for _ in range(2):
    #     input_batch = next(generate_input_items(INPUT_ITEM_BATCH_SIZE))

