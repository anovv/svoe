import itertools
import os
import time
import unittest

import tornado
from ray.util.client import ray
from tornado.ioloop import IOLoop

from data_catalog.indexer.actors.db import DbReader
from data_catalog.indexer.actors.queues import InputQueue, DownloadQueue
from data_catalog.indexer.actors.stats import Stats, DB_READS
from data_catalog.indexer.indexer import Indexer, WRITE_INDEX_ITEM_BATCH_SIZE
from data_catalog.indexer.sql.client import MysqlClient
from data_catalog.indexer.sql.models import add_defaults
from data_catalog.indexer.tasks.tasks import _index_df
from data_catalog.indexer.util import generate_input_items
from featurizer.features.loader.l2_snapshot_utils import get_snapshot_ts
from utils.pandas.df_utils import load_dfs, time_range
from utils.s3.s3_utils import load_df


class TestDataCatalogIndexer(unittest.TestCase):

    def test_parse_s3_keys(self):
        # TODO add multiproc
        batch_size = 1000
        exchange_symbol_unique_pairs = set()
        print('Loading generator...')
        generator = generate_input_items(batch_size)
        print('Generator loaded')
        for _ in range(5):
            batch = next(generator)
            for i in batch:
                exchange_symbol_unique_pairs.add((i['exchange'], i['symbol']))
        print(exchange_symbol_unique_pairs)

    def test_db_client(self):
        batch_size = 2
        print('Loading generator...')
        generator = generate_input_items(batch_size)
        print('Generator loaded')
        batch = next(generator)
        client = MysqlClient()
        client.create_tables()
        not_exist = client.check_exists(batch)
        print(f'Found {batch_size - len(not_exist)} items in db, {len(not_exist)} to write')
        dfs = load_dfs([i['path'] for i in not_exist])
        index_items = []
        for df, i in zip(dfs, not_exist):
            index_items.append(add_defaults(_index_df(df, i)))
        write_res = client.write_index_item_batch(index_items)
        print(f'Written {len(index_items)} to db, checking again...')
        not_exist = client.check_exists(batch)
        print(f'Found {batch_size - len(not_exist)} existing records in db')

    def test_db_reader(self):
        with ray.init(address='auto'):
            batch_size = 10
            num_batches = 2
            input_queue = InputQueue.remote()
            download_queue = DownloadQueue.remote()
            db_reader = DbReader.remote(input_queue, download_queue)
            print('Inited actors')
            print('Loading generator...')
            generator = generate_input_items(batch_size)
            print('Generator loaded')
            print('Queueing batch...')
            for i in range(num_batches):
                input_batch = next(generator)
                ray.get(input_queue.put.remote(input_batch))
                print(f'Queued {i + 1} batches')
            print('Done queueing')
            input_queue_size = ray.get(input_queue.size.remote())
            print(f'Input queue size: {input_queue_size}')
            db_reader.run.remote()
            print(f'Started DbReader actor')
            time.sleep(5)
            input_queue_size = ray.get(input_queue.size.remote())
            download_queue_size = ray.get(download_queue.size.remote())
            print(f'Input queue size: {input_queue_size}, Download queue size: {download_queue_size}')
            print('Done')

    def test_indexer(self):
        with ray.init(address='auto'):
            batch_size = WRITE_INDEX_ITEM_BATCH_SIZE
            num_batches = 2
            indexer = Indexer()
            indexer.run()
            print('Inited indexer')
            print('Loading generator...')
            generator = generate_input_items(batch_size)
            print('Generator loaded')
            print('Queueing batch...')
            inputs = []
            for i in range(num_batches):
                input_batch = next(generator)
                inputs.append(input_batch)
                indexer.pipe_input(input_batch)
                print(f'Queued {i + 1} batches')
            print('Done queueing')
            # wait for everything to process
            time.sleep(360)

            # check if index was written to db
            client = MysqlClient()
            not_exist = client.check_exists(list(itertools.chain(*inputs)))
            # should be 0
            print(len(not_exist))

    def test_bokeh_dashboard(self):
        with ray.init(address='auto'):
            stats = Stats.remote()
            stats.run.remote()
            time.sleep(2)
            for _ in range(10):
                ray.get(stats.inc_counter.remote(DB_READS))
                time.sleep(5)
            time.sleep(20)


if __name__ == '__main__':
    t = TestDataCatalogIndexer()
    t.test_bokeh_dashboard()
