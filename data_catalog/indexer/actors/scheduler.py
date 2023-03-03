import asyncio
import time
import uuid
import numpy as np
import heapq

from ray import workflow
from ray.util.client import ray
from ray.workflow import WorkflowStatus
from ray.workflow.event_listener import EventListener

from data_catalog.indexer.actors.db import DbActor, filter_existing, write_batch
from data_catalog.indexer.actors.stats import Stats, DOWNLOAD_TASKS_SCHEDULED, INDEX_TASKS_SCHEDULED, DOWNLOAD_TASK_TYPE, INDEX_TASK_TYPE, FILTER_TASK_TYPE, WRITE_DB_TASK_TYPE
from data_catalog.indexer.models import InputItemBatch
from data_catalog.indexer.tasks.tasks import load_df, index_df, gather_and_wait


# TODO use uvloop
@ray.remote
class Scheduler:

    def __init__(self, stats: Stats, db_actor: DbActor):
        self.read_queue = asyncio.Queue()
        self.input_queue = asyncio.Queue()

        self.is_running = True
        self.stats = stats
        self.db_actor = db_actor

        # TODo is this needed?
        self.workflow_task_ids = {} # maps workflow ids to task ids


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

    async def scheduler_loop(self):
        while self.is_running:
            if self.input_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue
            input_batch = await self.input_queue.get()
            batch_id = input_batch[0]['batch_id']
            workflow_id = f'workflow_{self.run_id}_{batch_id}'
            if workflow_id in self.workflow_task_ids:
                raise ValueError(f'Duplicate workflow scheduled: {workflow_id}')
            self.workflow_task_ids[workflow_id] = {}

            filter_task_id = f'{workflow_id}_{FILTER_TASK_TYPE}'
            self.workflow_task_ids[workflow_id][FILTER_TASK_TYPE] = [filter_task_id]

            # construct DAG
            _, filtered_items = workflow.continuation(filter_existing.options(**workflow.options(task_id=filter_task_id), num_cpus=0.01).bind(self.db_actor, input_batch, self.stats, filter_task_id))

            download_task_ids = []
            index_task_ids = []
            index_tasks = []

            for i in range(len(filtered_items)):
                item = filtered_items[i]
                download_task_id = f'{workflow_id}_{DOWNLOAD_TASK_TYPE}_{i}'
                download_task_ids.append(download_task_id)

                index_task_id = f'{workflow_id}_{INDEX_TASK_TYPE}_{i}'
                index_task_ids.append(index_task_id)

                extra = {'size_kb': item['size_kb']}

                download_task = load_df.options(**workflow.options(task_id=download_task_id), num_cpus=0.001).bind(item, self.stats, download_task_id, extra)
                index_task = index_df.options(**workflow.options(task_id=index_task_id), num_cpus=0.01).bind(download_task, item, self.stats, index_task_id, extra)
                index_tasks.append(index_task)

            self.workflow_task_ids[workflow_id][DOWNLOAD_TASK_TYPE] = download_task_ids
            self.workflow_task_ids[workflow_id][INDEX_TASK_TYPE] = index_task_ids

            gathered_index_items = gather_and_wait.bind(index_tasks)

            write_task_id = f'{workflow_id}_{WRITE_DB_TASK_TYPE}'
            self.workflow_task_ids[workflow_id][WRITE_DB_TASK_TYPE] = [write_task_id]

            dag = write_batch.options(**workflow.options(task_id=write_task_id), num_cpus=0.01).bind(self.db_actor, gathered_index_items, self.stats, write_task_id)

            # schedule execution
            # TODO is there a workflow callback for scheduled event?
            scheduled_events = []
            now = time.time()
            for _id in download_task_ids:
                scheduled_events.append({
                    'task_id': _id,
                    'event_type': DOWNLOAD_TASKS_SCHEDULED,
                    'timestamp': now
                })
            self.stats.events.remote(DOWNLOAD_TASK_TYPE, scheduled_events)
            scheduled_events = []
            now = time.time()
            for _id in index_task_ids:
                scheduled_events.append({
                    'task_id': _id,
                    'event_type': INDEX_TASKS_SCHEDULED,
                    'timestamp': now
                })
            self.stats.events.remote(INDEX_TASK_TYPE, scheduled_events)
            # TODO figure out what to do with write_status
            write_status_ref = workflow.run_async(dag, workflow_id=workflow_id)
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

    async def run(self):
        self.run_id = self._gen_run_id()
        reader = asyncio.create_task(self.read_loop())
        scheduler = asyncio.create_task(self.scheduler_loop())
        stats = asyncio.create_task(self.stats_loop())

        tasks = [reader, scheduler, stats]
        await asyncio.gather(*tasks)
        print('Scheduler finished')

    def _gen_run_id(self) -> str:
        # identifies current run
        # {Entry UUID}.{Unix time to nanoseconds}
        return f'{str(uuid.uuid4())}.{time.time():.9f}'

    def _list_workflows_for_current_run(self, statuses=None):
        all = workflow.list_all(statuses)
        # print(all)
        # print(self.run_id)
        # filter only for current run id
        # return list(filter(lambda wf: self.run_id in wf[0], to_wait))
        return all

    # TODO is this needed?
    def _get_task_type(self, task_id: str) -> str:
        if DOWNLOAD_TASK_TYPE in task_id:
            return DOWNLOAD_TASK_TYPE
        if INDEX_TASK_TYPE in task_id:
            return INDEX_TASK_TYPE
        if FILTER_TASK_TYPE in task_id:
            return FILTER_TASK_TYPE
        if WRITE_DB_TASK_TYPE in task_id:
            return WRITE_DB_TASK_TYPE
        raise ValueError(f'Unknown task_type for {task_id}')



