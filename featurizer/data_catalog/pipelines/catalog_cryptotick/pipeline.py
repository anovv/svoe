import asyncio
import functools
import math
import time
from typing import Dict

import ray
from tqdm import tqdm

from featurizer.sql.db_actor import DbActor
from featurizer.data_catalog.common.data_models.models import InputItemBatch
from featurizer.data_catalog.pipelines.catalog_cryptotick.tasks import load_split_catalog_store_df
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.data_source_metadata import DataSourceMetadata
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter
from featurizer.storage.data_store_adapter.remote_data_store_adapter import RemoteDataStoreAdapter

SPLIT_CHUNK_SIZE_KB = 100 * 1024


def poll_to_tqdm(total_files, chunk_size, max_bars=10):
    main_pbar = tqdm(desc='Total Progress', total=total_files)
    pbars = {}
    for i in range(max_bars):
        pbars[i] = [tqdm(position=i+1), None, {}]

    def get_bar_id(task_id):
        for bar_id in pbars:
            if pbars[bar_id][1] == task_id:
                return bar_id
        return None

    def get_first_empty_bar_id():
        for bar_id in pbars:
            if pbars[bar_id][1] is None:
                return bar_id
        return None

    actor = ray.get_actor('CatalogCryptotickPipeline')
    while True:
        all_stats = ray.get(actor.get_stats.remote())
        finished = set()
        for task_id in all_stats:
            stats = all_stats[task_id]
            status = stats['status']
            size = stats['size'] # size of file in s3

            approx_num_chunks = int(math.ceil(size * 27 / chunk_size)) # 27 is approx ratio of file_in_mem/file_in_s3

            if status == 'done':
                finished.add(task_id)
                bar_id = get_bar_id(task_id)
                if bar_id is not None:
                    # release
                    pbars[bar_id][1] = None
                    # add done info
                    pbar = pbars[bar_id][0]
                    extras = pbars[bar_id][2]
                    extras['write'] = round(stats['time_write'], 2)
                    pbar.set_description(f'Done {task_id}/{total_files}')
                    pbar.set_postfix(extras)
                continue

            bar_id = get_bar_id(task_id)
            if bar_id is None:
                bar_id = get_first_empty_bar_id()
                if bar_id is not None:
                    # occupy
                    pbars[bar_id][0].n = 0
                    pbars[bar_id][1] = task_id
                    pbars[bar_id][2] = {}
                else:
                    continue
            pbar = pbars[bar_id][0]
            extras = pbars[bar_id][2]
            if status == 'scheduled':
                pbar.set_description(f'Loading {task_id}/{total_files}...')
            elif status == 'load_finished':
                pbar.set_description(f'Preprocessing {task_id}/{total_files}...')
                extras['load'] = round(stats['time'], 2)
                pbar.set_postfix(extras)
            elif status == 'preproc_finished':
                pbar.set_description(f'Splitting {task_id}/{total_files}...')
                extras['preproc'] = round(stats['time'], 2)
                pbar.set_postfix(extras)
            elif status == 'splitting':
                pbar.set_description(f'Splitting {task_id}/{total_files}...')
                extras['split'] = round(stats['time_split'], 2)
                extras['store'] = round(stats['time_store'], 2)
                extras['n_stored'] = stats['num_stored']
                pbar.set_postfix(extras)
                pbar.n = stats['num_splits']
            pbar.total = approx_num_chunks
            pbar.refresh()

        main_pbar.n = len(finished)
        main_pbar.refresh()
        if len(finished) == total_files:
            break
        time.sleep(1)


@ray.remote
class CatalogCryptotickPipeline:

    def __init__(self, max_executing_tasks: int, db_actor: DbActor, data_store_adapter: DataStoreAdapter = RemoteDataStoreAdapter(), split_chunk_size_kb: int = SPLIT_CHUNK_SIZE_KB):
        self.is_running = True

        self.input_queue = asyncio.Queue()

        self.db_actor = db_actor
        self.max_executing_tasks = max_executing_tasks
        self.split_chunk_size_kb = split_chunk_size_kb
        self.data_store_adapter = data_store_adapter

        self.results_refs = []
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

            # TODO store DataSourceMetadata entry

            input_batch = await self.input_queue.get()
            _, filtered_items = await self.db_actor.filter_input_batch.remote(input_batch)

            if len(filtered_items) > 0:
                data_source_metadata = DataSourceMetadata(
                    owner_id='0',
                    key=filtered_items[0]['key'],
                    data_source_definition=filtered_items[0]['data_source_definition'],
                    params=filtered_items[0]['params'],
                    extras={}
                )
                await self.db_actor.store_metadata.remote([data_source_metadata])

            # mark files in db as ready for reporting
            for _ in range(len(input_batch[1]) - len(filtered_items)):
                task_id = len(self.stats)
                self.stats[task_id] = {'status': 'done', 'size': 1}

            for i in range(len(filtered_items)):
                item = filtered_items[i]
                raw_size_kb = item[DataSourceBlockMetadata.size_kb.name]

                while self.is_running and len(self.results_refs) >= self.max_executing_tasks:
                    await asyncio.sleep(0.1)

                if not self.is_running:
                    return

                task_id = len(self.stats)
                self.stats[task_id] = {'status': 'scheduled', 'size': raw_size_kb}

                def callback(event: Dict, task_id: int):
                    actor = ray.get_actor('CatalogCryptotickPipeline')
                    # TODO for some reason ray.get() on this blocks other tasks callbacks, why?
                    actor.update_stats.remote(event, task_id)

                self.results_refs.append(
                    load_split_catalog_store_df.remote(
                        item, self.split_chunk_size_kb, item['day'], self.db_actor, functools.partial(callback, task_id=task_id)
                    )
                )
                # wait = 1 if task_id%2 == 0 else 2
                # self.results_refs.append(mock_split.remote(functools.partial(callback, task_id=task_id), wait))

    # removes finished refs so Ray can release resources
    async def _process_results(self):
        while self.is_running:
            if len(self.results_refs) > 0:
                await self._process_one()
            else:
                # avoid waisting cpu
                await asyncio.sleep(1)

    async def _process_one(self):
        await asyncio.wait(self.results_refs, return_when=asyncio.FIRST_COMPLETED)
        # this should return immediately without blocking
        ready, remaining = ray.wait(self.results_refs, num_returns=1, fetch_local=False)
        self.results_refs = remaining

    async def wait_to_finish(self):
        print('Waiting for pipeline to finish before stopping')
        await asyncio.sleep(1)

        # wait for all input to start processing
        while self.input_queue.qsize() > 0:
            await asyncio.sleep(1)

        self.is_running = False
        while len(self.results_refs) > 0:
            await self._process_one()

        # These sleeps are for Ray to propagate prints to IO before killing everything
        await asyncio.sleep(1)
        print('Pipeline finished')
        await asyncio.sleep(1)

    async def run(self):
        scheduler = asyncio.create_task(self._schedule_tasks())
        process_results = asyncio.create_task(self._process_results())

        tasks = [scheduler, process_results]
        await asyncio.gather(*tasks)

    async def get_stats(self) -> Dict:
        await asyncio.sleep(0)
        return self.stats

    async def update_stats(self, event: Dict, task_id: int):
        await asyncio.sleep(0)
        t = event.get('time', None)
        if event['name'] == 'load_finished':
            self.stats[task_id]['status'] = 'load_finished'
            self.stats[task_id]['time'] = t
        elif event['name'] == 'preproc_finished':
            self.stats[task_id]['status'] = 'preproc_finished'
            self.stats[task_id]['time'] = t
        elif event['name'] == 'split_finished':
            if self.stats[task_id]['status'] != 'splitting':
                self.stats[task_id]['status'] = 'splitting'
                self.stats[task_id]['num_splits'] = 0
                self.stats[task_id]['num_stored'] = 0
                self.stats[task_id]['time_split'] = 0
                self.stats[task_id]['time_store'] = 0
            else:
                self.stats[task_id]['time_split'] = (self.stats[task_id]['time_split'] * self.stats[task_id]['num_splits'] + t) / (
                            self.stats[task_id]['num_splits'] + 1)
                self.stats[task_id]['num_splits'] += 1
        elif event['name'] == 'store_finished':
            self.stats[task_id]['time_store'] = (self.stats[task_id]['time_store'] * (self.stats[task_id]['num_stored']) + t) / (
            self.stats[task_id]['num_stored'] + 1)
            self.stats[task_id]['num_stored'] += 1
        elif event['name'] == 'write_finished':
            self.stats[task_id]['time_write'] = t
            self.stats[task_id]['status'] = 'done'
