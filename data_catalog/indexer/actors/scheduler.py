import asyncio
from threading import Thread

from ray import workflow
from ray.util.client import ray

from data_catalog.indexer.actors.db import DbActor, check_exists, write_batch
from data_catalog.indexer.actors.stats import Stats
from data_catalog.indexer.models import InputItemBatch
from data_catalog.indexer.tasks.tasks import load_df, index_df, gather_and_wait

# how many input batches one db actor can read in one db connection
DB_READ_BATCH_SIZE_IN_INPUT = 2


@ray.remote
class Scheduler:

    def __init__(self, stats: Stats, db_actor: DbActor):
        self.read_queue = asyncio.Queue()
        self.input_queue = asyncio.Queue()
        self.db_read_tasks_in_flight = []
        self.db_write_tasks_in_flight = []
        self.download_tasks_in_flight = []
        self.index_tasks_in_flight = []

        self.is_running = True
        self.stats = stats
        self.db_actor = db_actor

    async def pipe_input(self, input_item_batch: InputItemBatch):
        await self.read_queue.put(input_item_batch)

    async def read_loop(self):
        while self.is_running:
            if self.read_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue
            input_batch = await self.read_queue.get()
            await self.input_queue.put(input_batch)

    async def scheduler_loop(self):
        while self.is_running:
            if self.input_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue

            # TODO check for terminal item and stop execution

            db_read_batch = []
            while len(db_read_batch) != DB_READ_BATCH_SIZE_IN_INPUT and self.input_queue.qsize() != 0:
                input_batch = await self.input_queue.get()
                db_read_batch.extend(input_batch)

            # construct DAG
            non_exist_items = workflow.continuation(check_exists.bind(self.db_actor, db_read_batch))

            # TODO add download_tasks and index_tasks to global
            download_tasks = []
            for item in non_exist_items:
                download_tasks.append((load_df.bind(item, self.stats), item))

            index_tasks = []
            for download_task, input_item in download_tasks:
                index_tasks.append(index_df.bind(download_task, input_item, self.stats))

            gathered = gather_and_wait.bind(index_tasks)
            dag = write_batch.bind(self.db_actor, gathered)

            # schedule execution
            # write_status = await workflow.run_async(dag)
            dag.execute()
            # TODO figure out what to do with write_status

    async def run(self):
        reader = asyncio.create_task(self.read_loop())
        scheduler = asyncio.create_task(self.scheduler_loop())

        tasks = [reader, scheduler]
        await asyncio.gather(*tasks)
        print('Finished')













