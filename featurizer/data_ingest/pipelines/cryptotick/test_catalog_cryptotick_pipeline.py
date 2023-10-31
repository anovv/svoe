import functools
import unittest
from threading import Thread

import awswrangler as wr
import boto3.session
import ray

from featurizer.data_definitions.common.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.data_ingest.config import FeaturizerDataSourceFiles, FeaturizerDataIngestConfig, DataProviderName
from featurizer.data_ingest.models import InputItemBatch
from featurizer.data_ingest.utils.cryptotick_utils import process_cryptotick_timestamps
from featurizer.sql.client import FeaturizerSqlClient
from featurizer.sql.db_actor import create_db_actor
from featurizer.data_ingest.utils.cryptotick_utils import cryptotick_input_items, CRYPTOTICK_RAW_BUCKET_NAME
from featurizer.data_ingest.pipelines.cryptotick.pipeline import CatalogCryptotickPipeline, poll_to_tqdm
from featurizer.data_definitions.common.l2_book_incremental.cryptotick.utils import starts_with_snapshot, remove_snap, \
    get_snapshot_depth, mock_processed_cryptotick_df, \
    gen_split_l2_inc_df_and_pad_with_snapshot
from common.pandas.df_utils import concat
from common.s3.s3_utils import list_files_and_sizes_kb, load_df_s3, store_df_s3


class TestCatalogCryptotickPipeline(unittest.TestCase):

    def _store_test_df_to_s3(self):
        small_df_path = 's3://svoe-cryptotick-data/testing/small_df.parquet.gz'
        big_df = load_df_s3('s3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz')
        small_df = big_df.head(100000)
        store_df_s3(path=small_df_path, df=small_df)

    def test_pipeline(self):
        with ray.init(address='auto', ignore_reinit_error=True):
        # with ray.init(
        #         address='ray://127.0.0.1:10003',
        #         runtime_env={
        #             'py_modules': [featurizer, ray_cluster, data_catalog, utils],
        #             'excludes': ['*s3_svoe.test.1_inventory*']
        #         }):
            config = FeaturizerDataIngestConfig(
                provider_name=DataProviderName.CRYPTOTICK,
                batch_size=12,
                max_executing_tasks=10,
                data_source_files=[
                    FeaturizerDataSourceFiles(
                        data_source_definition=CryptotickL2BookIncrementalData,
                        files_and_sizes=[
                            ('limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                            ('limitbook_full/20230202/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                            ('limitbook_full/20230203/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                            ('limitbook_full/20230204/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024),
                        ]
                    )
                ]
            )
            db_actor = create_db_actor()
            # num_batches = 1
            # raw_files_and_sizes = list_files_and_sizes_kb(CRYPTOTICK_RAW_BUCKET_NAME)
            # raw_files_and_sizes = list(filter(lambda e: 'limitbook_full' in e[0], raw_files_and_sizes))
            # print([e[1] for e in raw_files_and_sizes])
            # raw_files_and_sizes = list(filter(lambda e: 'quotes' in e[0] and e[1] < 100 * 1024, raw_files_and_sizes))
            # print(len(raw_files_and_sizes))
            # raise
            # raw_files_and_sizes = [('limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', 252 * 1024))]
            # raw_files_and_sizes = [('trades/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', 228 * 1024)]
            # raw_files_and_sizes = [('trades/20230202/BINANCE_SPOT_BTC_USDT.csv.gz', 330 * 1024)]
            batches = cryptotick_input_items(config)
            pipeline = CatalogCryptotickPipeline.options(name='CatalogCryptotickPipeline').remote(
                max_executing_tasks=config.max_executing_tasks,
                db_actor=db_actor
            )

            Thread(target=functools.partial(poll_to_tqdm, total_files=config.num_files(), chunk_size=100 * 1024)).start()
            pipeline.run.remote()
            print('Queueing batches...')

            for i in range(len(batches)):
                ray.get(pipeline.pipe_input.remote(batches[i]))
            print('Done queueing')
            # wait for everything to process
            ray.get(pipeline.wait_to_finish.remote())
            # TODO assert index was written to db

    def test_split_trades_df(self):
        path = 's3://svoe-cryptotick-data/quotes/20230201/BINANCE_SPOT_BTC_USDT.csv.gz'
        split = path.split('/')
        suffix = split[len(split) - 1]
        # prefix = remove_suffix(path, suffix)
        prefix = path.removesuffix(suffix)
        session = boto3.session.Session()
        gen = wr.s3.read_csv(path=prefix, path_suffix=suffix, dataset=False, boto3_session=session, delimiter=';', chunksize=1024)
        df = next(gen)
        print(df.iloc[0])
        print(df.dtypes)
        df = process_cryptotick_timestamps(df)
        print(df.iloc[0])

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
        client = FeaturizerSqlClient()
        batch = InputItemBatch(0, [{'path': 's3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz'}])
        _, not_exist = client.filter_cryptotick_batch(batch)
        print(not_exist)

if __name__ == '__main__':
    t = TestCatalogCryptotickPipeline()
    t.test_pipeline()
    # t.test_split_trades_df()
    # t._store_test_df_to_s3()
    # t.test_split_l2_inc_df_and_pad_with_snapshot()
    # t.test_db_client()
    # t.test_dag()
    # t.test_tqdm()