import itertools
import time
import unittest

import ray

from data_catalog.common.utils.utils import make_index_item
from data_catalog.pipelines.index_cryptofeed.dag import IndexCryptofeedDag
from data_catalog.pipelines.pipeline_runner import PipelineRunner
from data_catalog.common.utils.sql.client import MysqlClient
from data_catalog.common.utils.cryptofeed.utils import generate_cryptofeed_input_items
from utils.pandas.df_utils import load_dfs


class TestIndexCryptofeedPipeline(unittest.TestCase):

    # TODO util this
    def test_parse_s3_keys(self):
        # TODO add multiproc
        batch_size = 1000
        exchange_symbol_unique_pairs = set()
        print('Loading generator...')
        generator = generate_cryptofeed_input_items(batch_size)
        print('Generator loaded')
        for _ in range(5):
            batch = next(generator)
            for i in batch:
                exchange_symbol_unique_pairs.add((i['exchange'], i['symbol']))
        print(exchange_symbol_unique_pairs)

    def test_db_client(self):
        batch_size = 2
        print('Loading generator...')
        generator = generate_cryptofeed_input_items(batch_size)
        print('Generator loaded')
        batch = next(generator)
        client = MysqlClient()
        client.create_tables()
        _, not_exist = client.filter_batch(batch)
        print(not_exist)
        print(f'Found {batch_size - len(not_exist)} items in db, {len(not_exist)} to write')
        dfs = load_dfs([i['path'] for i in not_exist])
        index_items = []
        for df, i in zip(dfs, not_exist):
            index_items.append(make_index_item(df, i, 'cryptofeed'))
        write_res = client.write_index_item_batch(index_items)
        print(f'Written {len(index_items)} to db, checking again...')
        _, not_exist = client.filter_batch(batch)
        print(f'Found {batch_size - len(not_exist)} existing records in db')
        assert len(not_exist) == 0


    def test_pipeline(self):
        with ray.init(address='auto'):
            batch_size = 50
            num_batches = 10
            runner = PipelineRunner()
            runner.run(IndexCryptofeedDag())
            print('Inited runner')
            print('Loading generator...')
            generator = generate_cryptofeed_input_items(batch_size)
            print('Generator loaded')
            print('Queueing batch...')
            inputs = []
            for i in range(num_batches):
                input_batch = next(generator)
                inputs.append(input_batch)
                runner.pipe_input(input_batch)
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

if __name__ == '__main__':
    t = TestIndexCryptofeedPipeline()
    t.test_pipeline()
    # t.test_db_client()

