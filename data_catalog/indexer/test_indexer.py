import itertools
import time
import unittest

from ray.util.client import ray

from data_catalog.indexer.actors.stats import Stats, FILTER_BATCH
from data_catalog.indexer.indexer import Indexer
from data_catalog.indexer.sql.client import MysqlClient
from data_catalog.indexer.sql.models import add_defaults
from data_catalog.indexer.tasks.tasks import _index_df
from data_catalog.indexer.util import generate_input_items
from utils.pandas.df_utils import load_dfs


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
        not_exist = client.filter_batch(batch)
        print(f'Found {batch_size - len(not_exist)} items in db, {len(not_exist)} to write')
        dfs = load_dfs([i['path'] for i in not_exist])
        index_items = []
        for df, i in zip(dfs, not_exist):
            index_items.append(add_defaults(_index_df(df, i)))
        write_res = client.write_index_item_batch(index_items)
        print(f'Written {len(index_items)} to db, checking again...')
        not_exist = client.filter_batch(batch)
        print(f'Found {batch_size - len(not_exist)} existing records in db')


    def test_indexer(self):
        with ray.init(address='auto'):
            batch_size = 50
            num_batches = 10
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

            # TODO this quits early if job is long
            # TODO make wait_for_completion func
            time.sleep(720)

            # check if index was written to db
            client = MysqlClient()
            not_exist = client.filter_batch(list(itertools.chain(*inputs)))
            # should be 0
            print(len(not_exist))

    def test_bokeh_dashboard(self):
        with ray.init(address='auto'):
            stats = Stats.remote()
            stats.run.remote()
            time.sleep(2)
            for _ in range(500):
                ray.get(stats.inc_task_events_counter.remote(FILTER_BATCH))
                time.sleep(0.1)
            time.sleep(20)


if __name__ == '__main__':
    t = TestDataCatalogIndexer()
    t.test_indexer()
