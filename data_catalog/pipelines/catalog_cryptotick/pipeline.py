import asyncio
import functools
import time
from typing import Dict

import ray
from tqdm import tqdm

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.utils.sql.models import DataCatalog
from data_catalog.pipelines.catalog_cryptotick.tasks import load_split_catalog_store_l2_inc_df

SPLIT_CHUNK_SIZE_KB = 100 * 1024


def poll_tqdm(pipeline_actor, total_files, chunk_size):
    main_pbar = tqdm(desc='Total Progress', total=total_files)
    pbars = {}
    max_bars = 10
    for i in range(max_bars):
        # pbar, and owner_id
        pbars[i] = [tqdm(position=i+1), None]

    task_id_to_bar_id = {}

    while True:
        all_stats = ray.get(pipeline_actor.get_stats.remote())
        print(all_stats)
        num_finished = 0
        for task_id in all_stats:
            stats = all_stats[task_id]
            status = stats['status']
            size = stats['size'] # size of file on disk

            approx_num_chunks = size * 27 / chunk_size

            if status == 'done':
                num_finished += 1
                if task_id in task_id_to_bar_id:
                    bar_id = task_id_to_bar_id[task_id]
                    pbars[bar_id][0].reset()
                    pbars[bar_id][1] = None
                    del task_id_to_bar_id[task_id]
                    continue
            else:
                if task_id not in task_id_to_bar_id:
                    # find available bar_id
                    for bar_id in pbars:
                        if pbars[bar_id][1] is None:
                            task_id_to_bar_id[task_id] = bar_id
                            pbars[bar_id][1] = task_id
                            pbars[bar_id][0].total = approx_num_chunks
                            pbars[bar_id][0].refresh()
                            break

            bar_id = task_id_to_bar_id[task_id]
            pbar = pbars[bar_id][0]
            if status == 'scheduled':
                pbar.set_description(f'Loading {task_id}/{total_files}...')
            elif status == 'load_finished':
                pbar.set_description(f'Preprocessing {task_id}/{total_files}...')
                pbar.set_postfix({'load_time': stats['time']})
            elif status == 'preproc_finished':
                pbar.set_description(f'Splitting {task_id}/{total_files}...')
                p = pbar.postfix
                p['preproc_time'] = stats['time']
                pbar.set_postfix(p)
            elif status == 'split_finished':
                p = pbar.postfix
                p['time_split'] = stats['time_split']
                pbar.set_postfix(p)
            elif status == 'store_finished':
                p = pbar.postfix
                p['time_store'] = stats['time_store']
                pbar.set_postfix(p)
                pbar.n = stats['num_splits']
            pbar.refresh()

        main_pbar.n = num_finished
        main_pbar.refresh()
        if num_finished == total_files:
            break
        time.sleep(1)


@ray.remote
class CatalogCryptotickPipeline:

    def __init__(self, max_executing_tasks: int, db_actor: DbActor, split_chunk_size_kb: int = SPLIT_CHUNK_SIZE_KB):
        self.is_running = True

        self.input_queue = asyncio.Queue()

        self.db_actor = db_actor
        self.max_executing_tasks = max_executing_tasks
        self.split_chunk_size_kb = split_chunk_size_kb

        self.tasks_refs = []
        self.stats = {}

    async def pipe_input(self, input_item_batch: InputItemBatch):
        if not self.is_running:
            raise ValueError('Runner is marked as stopped, no more input is accepted')

        # wait to avoid backlog
        while self.is_running and self.input_queue.qsize() > 2:
            await asyncio.sleep(0.1)
            continue
        await self.input_queue.put(input_item_batch)
        print(f'Queued {input_item_batch[0]}')

    async def _schedule_tasks(self):
        while self.is_running:
            if self.input_queue.qsize() == 0:
                await asyncio.sleep(0.1)
                continue
            input_batch = await self.input_queue.get()

            _, filtered_items = await self.db_actor.filter_batch.remote(input_batch)

            for i in range(len(filtered_items)):
                item = filtered_items[i]
                raw_size_kb = item[DataCatalog.size_kb.name]
                # stats_extra = {'size_kb': raw_size_kb} # TODO report load size for throughput

                if len(self.tasks_refs) < self.max_executing_tasks:
                    task_id = len(self.stats)
                    self.stats[task_id] = {'status': 'scheduled', 'size': raw_size_kb}

                    def callback(event: Dict, task_id: int):
                        print(event)
                        task_stats = self.stats[task_id]
                        t = event.get('time', None)
                        if event['name'] == 'load_finished':
                            task_stats['status'] = 'load_finished'
                            task_stats['time'] = t
                        elif event['name'] == 'preproc_finished':
                            task_stats['status'] = 'preproc_finished'
                            task_stats['time'] = t
                        elif event['name'] == 'split_finished':
                            if task_stats['status'] != 'splitting':
                                task_stats['status'] = 'splitting'
                                task_stats['num_splits'] = 0
                                task_stats['time_split'] = 0
                                task_stats['time_store'] = 0
                            else:
                                task_stats['time_split'] = (task_stats['time_split'] * task_stats['num_splits'] + t)/(task_stats['num_splits'] + 1)
                                task_stats['num_splits'] += 1
                        elif event['name'] == 'store_finished':
                            task_stats['time_store'] = (task_stats['time_store'] * (task_stats['num_splits'] - 1) + t)/(task_stats['num_splits'])
                        elif event['name'] == 'write_finished':
                            task_stats['status'] = 'done'
                        print(self.stats)

                    self.tasks_refs.append(
                        load_split_catalog_store_l2_inc_df.remote(
                            item, self.split_chunk_size_kb, item['date'], self.db_actor, functools.partial(callback, task_id=task_id)
                        )
                    )
                else:
                    while self.is_running and len(self.tasks_refs) >= self.max_executing_tasks:
                        await asyncio.sleep(0.1)


    # checks which dags finished and removes refs so Ray can release resources
    async def _process_results(self):
        while self.is_running:
            if len(self.tasks_refs) > 0:
                ready, remaining = await asyncio.wait(self.tasks_refs, return_when=asyncio.FIRST_COMPLETED)
                self.tasks_refs = remaining
            await asyncio.sleep(1)

    async def run(self):
        scheduler = asyncio.create_task(self._schedule_tasks())
        process_results = asyncio.create_task(self._process_results())

        tasks = [scheduler, process_results]
        await asyncio.gather(*tasks)
        print('Scheduler finished')

    async def wait_to_finish(self):
        print('Waiting for pipeline to finish before stopping')
        await asyncio.sleep(1)

        # wait for all input to start processing
        while self.input_queue.qsize() > 0:
            await asyncio.sleep(1)

        self.is_running = False
        while len(self.tasks_refs) > 0:
            # TODO this blocks io
            ready, remaining = await asyncio.wait(self.tasks_refs, return_when=asyncio.ALL_COMPLETED)
            self.tasks_refs = remaining

        # These sleeps are for Ray to propagate prints to IO before killing everything
        await asyncio.sleep(1)
        print('Pipeline finished')
        await asyncio.sleep(1)

    async def get_stats(self) -> Dict:
        # await asyncio.sleep(0)
        return self.stats
