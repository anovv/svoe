import unittest

import numpy as np

from svoe.featurizer.data_definitions.common.l2_book_incremental.cryptotick.utils import preprocess_l2_inc_df
from svoe.featurizer.featurizer_utils.testing_utils import mock_l2_book_delta_data_and_meta, mock_trades_data_and_meta
from svoe.common.pandas.df_utils import gen_split_df_by_mem, get_size_kb, concat
from svoe.common.s3.s3_utils import load_df_s3


class TestDataIngestUtils(unittest.TestCase):

    def test_cryptotick_df_split(self):
        path = 's3://svoe-junk/27606-BITSTAMP_SPOT_BTC_EUR.csv.gz'
        date_str = '20230201'
        print('Started loading')
        df = load_df_s3(path)
        print('Finished loading, started processing')
        df = preprocess_l2_inc_df(df, date_str)
        print('Finished loading, started preprocessing')

        split_size_kb = 100 * 1024
        split_gen = gen_split_df_by_mem(df, split_size_kb)
        splits = []
        i = 0
        for split in split_gen:
            print(f'Split {i}')
            splits.append(split)
            if i > 0:
                assert splits[i - 1].iloc[-1]['timestamp'] != splits[i].iloc[0]['timestamp']
            i += 1

        print(len(splits))
        print(f'Avg split size {np.mean([get_size_kb(split) for split in splits])}kb')

        assert concat(splits).equals(df)

    # TODO util this
    def test_cryptofeed_df_split(self):
        l2_data, _ = mock_l2_book_delta_data_and_meta()
        l2_dfs = list(l2_data.values())[0]

        trades_data, _ = mock_trades_data_and_meta()
        trades_dfs = list(trades_data.values())[0]

        l2_split_size_kb = 300
        l2_split_sizes = []
        for l2_df in l2_dfs:
            l2_split_gen = gen_split_df_by_mem(l2_df, l2_split_size_kb)
            splits = []
            for split_df in l2_split_gen:
                l2_split_sizes.append(get_size_kb(split_df))
                splits.append(split_df)

            for i in range(1, len(splits)):
                assert splits[i - 1].iloc[-1]['timestamp'] != splits[i].iloc[0]['timestamp']

            concated = concat(splits)
            assert concated.equals(l2_df)
        print(f'Avg L2 split size:{np.mean(l2_split_sizes)}')

        trades_split_size_kb = 10
        trades_split_sizes = []
        for trades_df in trades_dfs:
            trades_split_gen = gen_split_df_by_mem(trades_df, trades_split_size_kb)
            splits = []
            for split_df in trades_split_gen:
                trades_split_sizes.append(get_size_kb(split_df))
                splits.append(split_df)

            for i in range(1, len(splits)):
                assert splits[i - 1].iloc[-1]['timestamp'] != splits[i].iloc[0]['timestamp']

            concated = concat(splits)
            assert concated.equals(trades_df)

        print(f'Avg Trades split size:{np.mean(trades_split_sizes)}')


if __name__ == '__main__':
    # unittest.main()
    t = TestDataIngestUtils()
    t.test_cryptofeed_df_split()
    t.test_cryptotick_df_split()