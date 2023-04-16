import asyncio
import time
import uuid

import ray
from ray.workflow import WorkflowStatus

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.actors.stats import Stats

# TODO use uvloop ?
from data_catalog.pipelines.dag import Dag


@ray.remote
class Scheduler:

    def __init__(self, stats: Stats, db_actor: DbActor):
        self.read_queue = asyncio.Queue()
        self.input_queue = asyncio.Queue()

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
            write_status_ref = _dag.execute()
            # TODO figure out what to do with write_status
            # TODO add cleanup coroutine for self.workflow_task_ids when finished

    async def stop(self):
        self.is_running = False
        await self._wait_for_workflows_to_finish()
        print('All workflows finished')

    async def _wait_for_workflows_to_finish(self):
        to_wait = self._list_workflows_for_current_run({WorkflowStatus.RUNNING, WorkflowStatus.PENDING})
        while len(to_wait) != 0:
            print('Waiting')
            print(to_wait)
            await asyncio.sleep(0.1)
            to_wait = self._list_workflows_for_current_run({WorkflowStatus.RUNNING, WorkflowStatus.PENDING})

    async def run(self, dag: Dag):
        self.run_id = self._gen_run_id()
        reader = asyncio.create_task(self.read_loop())
        scheduler = asyncio.create_task(self.scheduler_loop(dag))
        stats = asyncio.create_task(self.stats_loop())

        tasks = [reader, scheduler, stats]
        await asyncio.gather(*tasks)
        print('Scheduler finished')

    def _gen_run_id(self) -> str:
        # identifies current run
        # {Entry UUID}.{Unix time to nanoseconds}
        return f'{str(uuid.uuid4())}.{time.time():.9f}'

    def _list_workflows_for_current_run(self, statuses=None):
        all = []
        # all = workflow.list_all(statuses)
        # print(all)
        # print(self.run_id)
        # TODO filter only for current run id
        # return list(filter(lambda wf: self.run_id in wf[0], to_wait))
        return all
