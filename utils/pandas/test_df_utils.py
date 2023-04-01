import unittest

import joblib

from utils.pandas.df_utils import store_df, get_cached_df, load_df


class TestDfUtils(unittest.TestCase):

    def test_store_df(self):

        big_df_path = 's3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz'
        key = joblib.hash(big_df_path + str(0))
        # TODO is this processed or not?
        big_df = get_cached_df(key)
        path = 's3://svoe-junk/big_cryptotick_df.parquet.gz'
        assert big_df is not None
        print(store_df(path, big_df))
        loaded = load_df(path, use_cache=False)
        print(loaded.head(10))
        # assert loaded.equals(big_df)
        # diff = big_df.compare(loaded, keep_shape=True)
        # print(diff)
        print(loaded.info())
        print(big_df.info())


if __name__ == '__main__':
    t = TestDfUtils()
    t.test_store_df()