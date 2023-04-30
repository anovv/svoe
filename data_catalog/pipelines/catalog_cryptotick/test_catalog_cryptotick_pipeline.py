import time
import unittest
from typing import Tuple, List, Dict

import pandas as pd
import ray

import data_catalog
import featurizer
import ray_cluster
import utils
from data_catalog.common.actors.db import DbActor
from data_catalog.common.utils.cryptotick.utils import cryptotick_input_items
from data_catalog.common.utils.sql.client import MysqlClient
from featurizer.features.data.l2_book_incremental.cryptotick.utils import starts_with_snapshot, remove_snap, \
    get_snapshot_depth, mock_processed_cryptotick_df, \
    gen_split_l2_inc_df_and_pad_with_snapshot
from utils.pandas.df_utils import concat, load_df, store_df
from tasks import load_split_catalog_store_l2_inc_df


class TestCatalogCryptotickPipeline(unittest.TestCase):

    def _store_test_df_to_s3(self):
        small_df_path = 's3://svoe-cryptotick-data/testing/small_df.parquet.gz'
        big_df = load_df('s3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz')
        small_df = big_df.head(100000)
        store_df(path=small_df_path, df=small_df)

    def test_pipeline(self):
        with ray.init(address='auto', ignore_reinit_error=True):
        # with ray.init(
        #         address='ray://127.0.0.1:10003',
        #         runtime_env={
        #             'py_modules': [featurizer, ray_cluster, data_catalog, utils],
        #             'excludes': ['*s3_svoe.test.1_inventory*']
        #         }):
            db_actor = DbActor.remote()
            batch_size = 1
            num_batches = 1
            # raw_files = list_files_and_sizes_kb(CRYPTOTICK_RAW_BUCKET_NAME)
            raw_files_and_sizes = [
                # ('limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                # ('limitbook_full/20230202/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                # ('limitbook_full/20230203/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                ('limitbook_full/20230204/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
            ]
            # raw_files_and_sizes = [('s3://svoe-cryptotick-data/testing/small_df.parquet.gz', 470)]
            batches = cryptotick_input_items(raw_files_and_sizes, batch_size)
            print('Queueing batches...')
            time.sleep(5)
            for i in range(num_batches):
                _, items = batches[i]

                ray.get(load_split_catalog_store_l2_inc_df.remote(items[0], 100 * 1024, '01-02-2023', db_actor))
                print(f'Queued {i + 1} batches')
            print('Done queueing')

            time.sleep(10000)
            # wait for everything to process
            # runner.wait_to_finish()
            # TODO assert index was written to db

    def test_split_l2_inc_df_and_pad_with_snapshot(self):
        # TODO merge this with stuff in test_calculator
        processed_df = mock_processed_cryptotick_df()

        # TODO split_size_kb == 2*1024 results in update_type == SUB not finding price level in a book?
        #  same for 512
        #  smaller splits seem to also work (1*1024 works)
        split_size_kb = 2 * 1024
        gen = gen_split_l2_inc_df_and_pad_with_snapshot(processed_df, split_size_kb)
        splits_to_concat = []
        i = 0
        for split in gen:
            assert starts_with_snapshot(split)
            bids_depth, asks_depth = get_snapshot_depth(split)
            print(bids_depth, asks_depth)
            assert bids_depth <= 5000
            assert asks_depth <= 5000
            if i > 0:
                split = remove_snap(split)
            i += 1
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

    def test_dag(self):
        # @ray.remote(num_cpus=0.1, num_returns=2, resources={'worker_size_large': 1, 'instance_spot': 1})
        # def t() -> Tuple[List[ObjectRef], List[Dict]]:
        #     return [ray.put(pd.DataFrame({})), ray.put(pd.DataFrame({}))], [{'t1': 1}, {'t2': 2}]


        @ray.remote(num_cpus=0.1, num_returns=2, resources={'worker_size_large': 1, 'instance_spot': 1})
        def t() -> Tuple[List[pd.DataFrame], List[Dict]]:
            return [pd.DataFrame({}), pd.DataFrame({})], [{'t1': 1}, {'t2': 2}]


        # with ray.init(address='auto', ignore_reinit_error=True):
        with ray.init(
                address='ray://127.0.0.1:10002',
                runtime_env={
                    'py_modules': [featurizer, ray_cluster, data_catalog, utils],
                    'excludes': ['*s3_svoe.test.1_inventory*']
                }):

            # a1 = DbActor.options(name="DbActor", get_if_exists=True).bind()
            r1, r2 = t.remote()
            ray.wait([r1], fetch_local=False)
            f = ray.get(r1)
            print(f)
            time.sleep(720)


if __name__ == '__main__':
    t = TestCatalogCryptotickPipeline()
    t.test_pipeline()
    # t._store_test_df_to_s3()
    # t.test_split_l2_inc_df_and_pad_with_snapshot()
    # t.test_db_client()
    # t.test_dag()