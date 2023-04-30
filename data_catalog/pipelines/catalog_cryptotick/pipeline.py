import asyncio

import ray
from ray import workflow

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.pipelines.catalog_cryptotick.tasks import load_split_catalog_l2_inc_df, store_df

SPLIT_CHUNK_SIZE_KB = 100 * 1024


class CatalogCryptotickPipeline:

    def __int__(self, throughput: int, db_actor: DbActor):
        self.is_running = True

        self.read_queue = asyncio.Queue()
        self.input_queue = asyncio.Queue()

        self.db_actor = db_actor
        self.throughput = throughput

        self.split_tasks_executing = []
        self.split_tasks_done = asyncio.Queue()

        self.store_tasks_executing = []
        self.store_tasks_done = []

    async def pipe_input(self, input_item_batch: InputItemBatch):
        if not self.is_running:
            raise ValueError('Runner is marked as stopped, no more input is accepted')

        # wait to avoid backlog
        while self.is_running and self.read_queue.qsize() > 2:
            await asyncio.sleep(0.1)
            continue
        await self.read_queue.put(input_item_batch)

    async def read_loop(self):
        while self.is_running:
            if self.read_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue
            input_batch = await self.read_queue.get()
            await self.input_queue.put(input_batch)

    async def schedule_split_tasks(self):
        while self.is_running:
            if self.input_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue

            input_batch = await self.input_queue.get()
            _, filtered_items = ray.get(self.db_actor.filter_batch.options(num_cpus=0.01).remote(input_batch))

            for i in range(len(filtered_items)):
                item = filtered_items[i]
                # raw_size_kb = item[DataCatalog.size_kb.name]
                # stats_extra = {'size_kb': raw_size_kb} # TODO report load size for throughput

                if len(self.split_tasks_executing) <= self.throughput:
                    self.split_tasks_executing.append(
                        load_split_catalog_l2_inc_df.remote(
                            item, SPLIT_CHUNK_SIZE_KB, item['date']
                        )
                    )
                else:
                    while self.is_running:
                        ready, remaining = ray.wait(self.split_tasks_executing, timeout=0, num_returns=len(self.split_tasks_executing), fetch_local=False)
                        self.split_tasks_executing = remaining
                        for ref in ready:
                            await self.split_tasks_done.put(ref)
                        await asyncio.sleep(1)

    async def schedule_store_tasks(self):
        while self.is_running:
            if self.split_tasks_done.qsize() == 0:
                await asyncio.sleep(0.1)
                continue

            splits, catalog_items, length = await self.split_tasks_done.get()

            for i in range(length):

                store_task = store_df.bind(
                    splits, catalog_items, length
                )
                store_tasks.append(store_task)

            gathered_store_tasks = gather_and_wait.options(num_cpus=0.01).bind(
                store_tasks
            )

            write_db_task = write_batch.options(num_cpus=0.01).bind(
                db_actor, catalog_items
            )

            dag_nodes.append(chain_no_ret.options(num_cpus=0.01, resources={'worker_size_large': 1, 'instance_spot': 1}).bind(
                gathered_store_tasks, write_db_task
            ))

            print(len(dag_nodes))

            return gather_and_wait.options(num_cpus=0.01, resources={'worker_size_large': 1, 'instance_spot': 1}).bind(dag_nodes)
