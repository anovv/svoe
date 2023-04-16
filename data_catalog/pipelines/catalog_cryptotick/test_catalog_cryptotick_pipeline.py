import itertools
import os
import time
import unittest

import joblib
import ray

import data_catalog
import featurizer
import ray_cluster
import utils
from data_catalog.common.actors.db import DbActor
from data_catalog.common.actors.scheduler import Scheduler
from data_catalog.common.actors.stats import Stats
from data_catalog.common.utils.cryptotick.utils import cryptotick_input_items
from data_catalog.common.utils.sql.client import MysqlClient
from data_catalog.common.utils.sql.models import make_catalog_item
from data_catalog.pipelines.catalog_cryptotick.dag import CatalogCryptotickDag
from data_catalog.pipelines.pipeline_runner import PipelineRunner
from featurizer.features.data.l2_book_incremental.cryptotick.utils import starts_with_snapshot, remove_snap, \
    get_snapshot_depth, preprocess_l2_inc_df, split_l2_inc_df_and_pad_with_snapshot, mock_processed_cryptotick_df
from utils.pandas.df_utils import get_cached_df, concat, load_df, store_df


class TestCatalogCryptotickPipeline(unittest.TestCase):

    def _store_test_df_to_s3(self):
        small_df_path = 's3://svoe-cryptotick-data/testing/small_df.parquet.gz'
        big_df = load_df('s3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', extension='csv')
        small_df = big_df.head(100000)
        store_df(path=small_df_path, df=small_df)



    def test_pipeline(self):
        # with ray.init(address='auto', ignore_reinit_error=True):
        with ray.init(
                address='ray://127.0.0.1:10002',
                runtime_env={
                    'py_modules': [featurizer, ray_cluster, data_catalog, utils],
                    # 'pip': ['cache-df', 'ciso8601'],
                    'excludes': ['*s3_svoe.test.1_inventory*']
                }):
            batch_size = 1
            num_batches = 1
            runner = PipelineRunner()
            runner.run(CatalogCryptotickDag())
            print('Inited runner')
            # raw_files = list_files_and_sizes_kb(CRYPTOTICK_RAW_BUCKET_NAME)
            # raw_files_and_sizes = [('limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024)]
            raw_files_and_sizes = [('s3://svoe-cryptotick-data/testing/small_df.parquet.gz', 470)]
            batches = cryptotick_input_items(raw_files_and_sizes, batch_size)
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
            not_exist = client.filter_cryptotick_batch(list(itertools.chain(*inputs)))
            # TODO should be 0
            print(len(not_exist))

    def test_split_l2_inc_df_and_pad_with_snapshot(self):
        # TODO merge this with stuff in test_calculator
        processed_df = mock_processed_cryptotick_df()

        # TODO split_size_kb == 2*1024 results in update_type == SUB not finding price level in a book?
        #  same for 512
        #  smaller splits seem to also work (1*1024 works)
        split_size_kb = 2 * 1024
        splits_with_snapshot = split_l2_inc_df_and_pad_with_snapshot(processed_df, split_size_kb)
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
        assert processed_df.equals(concated)

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
    # t._store_test_df_to_s3()
    # t.test_split_l2_inc_df_and_pad_with_snapshot()
    # t.test_db_client()