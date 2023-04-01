import unittest

import joblib

from data_catalog.common.utils.cryptotick.utils import cryptotick_input_items
from data_catalog.common.utils.sql.models import make_catalog_item
from data_catalog.pipelines.catalog_cryptotick.dag import split_l2_inc_df_and_pad_with_snapshot
from featurizer.features.data.l2_book_incremental.cryptotick.utils import starts_with_snapshot, remove_snap, \
    get_snapshot_depth, preprocess_l2_inc_df
from utils.pandas.df_utils import get_cached_df, concat


class TestCatalogCryptotickPipeline(unittest.TestCase):

    def test_pipeline(self):
        batches = cryptotick_input_items(10)
        # catalog_item = make_catalog_item(batches[0])

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


if __name__ == '__main__':
    t = TestCatalogCryptotickPipeline()
    t.test_pipeline()
    # t.test_split_l2_inc_df_and_pad_with_snapshot()