import asyncio
import time
import uuid

import ray

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.actors.stats import Stats

# TODO use uvloop ?
from data_catalog.pipelines.dag import Dag


# @ray.remote(resources={'worker_size_small': 1, 'instance_on_demand': 1})
@ray.remote
class Scheduler:

    def __init__(self, stats: Stats, db_actor: DbActor):
        self.read_queue = asyncio.Queue()
        self.input_queue = asyncio.Queue()

        self.is_running = True
        self.stats = stats
        self.db_actor = db_actor
        self.result_refs = []

    async def pipe_input(self, input_item_batch: InputItemBatch):
        if not self.is_running:
            raise ValueError('Runner is marked as stopped, no more input is accepeted')
        await self.read_queue.put(input_item_batch)

    async def read_loop(self):
        while self.is_running:
            if self.read_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue
            input_batch = await self.read_queue.get()
            await self.input_queue.put(input_batch)

    async def stats_loop(self):
        while self.is_running:
            await asyncio.sleep(0.1)

    async def scheduler_loop(self, dag: Dag):
        while self.is_running:
            if self.input_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue
            input_batch = await self.input_queue.get()
            batch_id = input_batch[0]['batch_id']
            dag_id = f'dag_{self.run_id}_{batch_id}'
            _dag = dag.get(dag_id, input_batch, self.stats, self.db_actor)

            # TODO figure out what to do with result_refs
            self.result_refs.append(_dag.execute())


    # checks which dags finished and removes refs so Ray can release resources
    async def process_results_loop(self):
        while self.is_running:
            ready, remaining = ray.wait(self.result_refs, timeout=0, num_returns=1, fetch_local=False)
            self.result_refs = remaining
            await asyncio.sleep(1)


    async def stop(self):
        print('Waiting for runner to finish before stopping')

        # wait for input q and read q to start processing
        while self.input_queue.qsize() > 0 or self.read_queue.qsize() > 0:
            await asyncio.sleep(1)

        # TODO this will stop stats loop and hence stats actor early? Have separate flags?
        self.is_running = False
        while len(self.result_refs) > 0:
            ready, remaining = ray.wait(self.result_refs, num_returns=len(self.result_refs), fetch_local=False, timeout=30)
            self.result_refs = remaining

        # These sleeps are for Ray to propagate prints to IO before killing everything
        await asyncio.sleep(1)
        print('Runner finished')
        await asyncio.sleep(1)


    async def run(self, dag: Dag):
        self.run_id = self._gen_run_id()
        reader = asyncio.create_task(self.read_loop())
        scheduler = asyncio.create_task(self.scheduler_loop(dag))
        stats = asyncio.create_task(self.stats_loop())
        process_results = asyncio.create_task(self.process_results_loop())

        tasks = [reader, scheduler, stats, process_results]
        await asyncio.gather(*tasks)
        print('Scheduler finished')

    def _gen_run_id(self) -> str:
        # identifies current run
        # {Entry UUID}.{Unix time to nanoseconds}
        return f'{str(uuid.uuid4())}.{time.time():.9f}'
