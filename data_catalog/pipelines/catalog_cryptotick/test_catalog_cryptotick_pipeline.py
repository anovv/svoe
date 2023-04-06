import itertools
import time
import unittest

import joblib

from data_catalog.common.utils.cryptotick.utils import cryptotick_input_items
from data_catalog.common.utils.sql.client import MysqlClient
from data_catalog.common.utils.sql.models import make_catalog_item
from data_catalog.pipelines.catalog_cryptotick.dag import CatalogCryptotickDag
from data_catalog.pipelines.pipeline_runner import PipelineRunner
from featurizer.features.data.l2_book_incremental.cryptotick.utils import starts_with_snapshot, remove_snap, \
    get_snapshot_depth, preprocess_l2_inc_df, split_l2_inc_df_and_pad_with_snapshot
from utils.pandas.df_utils import get_cached_df, concat


class TestCatalogCryptotickPipeline(unittest.TestCase):

    def test_pipeline(self):
        batch_size = 1
        num_batches = 1
        runner = PipelineRunner()
        runner.run(CatalogCryptotickDag())
        print('Inited runner')
        batches = cryptotick_input_items(batch_size)
        print('Queueing batch...')
        inputs = []
        time.sleep(5)
        for i in range(num_batches):
            input_batch = batches[i]
            inputs.append(input_batch)
            runner.pipe_input(input_batch)
            print(f'Queued {i + 1} batches')
        print('Done queueing')
        # wait for everything to process

        # TODO this quits early if job is long
        # TODO make wait_for_completion func
        time.sleep(720 * 10)

        # check if index was written to db
        client = MysqlClient()
        not_exist = client.filter_batch(list(itertools.chain(*inputs)))
        # TODO should be 0
        print(len(not_exist))

    # TODO assertions
    def test_construct_s3_path(self):
        batch_size = 10
        batches = cryptotick_input_items(batch_size)
        _, first_batch = batches[0]
        big_df_path = 's3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz'
        key = joblib.hash(big_df_path + str(0))
        # TODO is this processed or not?
        big_df = get_cached_df(key)
        date_str = '20230201'
        big_df = preprocess_l2_inc_df(big_df, date_str)
        catalog_item = make_catalog_item(big_df, first_batch[0])
        print(catalog_item.path)

    def test_split_l2_inc_df_and_pad_with_snapshot(self):
        # TODO merge this with stuff in test_calculator
        date_str = '20230201'
        big_df_path = 's3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz'
        key = joblib.hash(big_df_path + str(0))
        # TODO is this processed or not?
        big_df = get_cached_df(key)
        big_df = preprocess_l2_inc_df(big_df, date_str)

        splits_with_snapshot = split_l2_inc_df_and_pad_with_snapshot(big_df, 25 * 1024)
        splits_to_concat = []
        for i in range(len(splits_with_snapshot)):
            split = splits_with_snapshot[i]
            assert starts_with_snapshot(split)
            bids_depth, asks_depth = get_snapshot_depth(split)
            assert bids_depth == 5000
            assert asks_depth == 5000
            if i > 0:
                split = remove_snap(split)
            splits_to_concat.append(split)

        concated = concat(splits_to_concat)
        assert big_df.equals(concated)

    # TODO asserts, write mock data
    def test_db_client(self):
        client = MysqlClient()
        client.create_tables()
        batch = ({'batch_id': 0}, [{'path': 's3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz'}])
        _, not_exist = client.filter_cryptotick_batch(batch)
        print(not_exist)


if __name__ == '__main__':
    t = TestCatalogCryptotickPipeline()
    t.test_pipeline()
    # t.test_split_l2_inc_df_and_pad_with_snapshot()
    # t.test_db_client()