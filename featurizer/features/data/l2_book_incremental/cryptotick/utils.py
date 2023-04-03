from typing import Optional, List, Tuple
from utils.pandas.df_utils import is_ts_sorted

import ciso8601
import pandas as pd


# see https://www.cryptotick.com/Faq
# this is a heavy compute operation, 5Gb df takes 4-5 mins
def preprocess_l2_inc_df(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    # date_str = '20230201'
    datetime_str = f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}T'  # yyyy-mm-dd + 'T'

    def _to_ts(s):
        return ciso8601.parse_datetime(f'{datetime_str}{s}Z').timestamp()

    df['timestamp'] = df['time_exchange'].map(lambda x: _to_ts(x))
    df['receipt_timestamp'] = df['time_coinapi'].map(lambda x: _to_ts(x))
    # for some reason raw cryptotick dates are not sorted
    # don't use inplace=True as it harms perf https://sourcery.ai/blog/pandas-inplace/
    df = df.sort_values(by=['timestamp'], ignore_index=True)
    if not is_ts_sorted(df):
        raise ValueError('Unable to sort df by timestamp')

    df = df.drop(columns=['time_exchange', 'time_coinapi'])

    # cryptotick l2_inc should not contain any order_id info
    if pd.notna(df['order_id']).sum() != 0:
        raise ValueError('Cryptotick l2_inc df should not contain order_id values')

    df = df.drop(columns=['order_id'])

    # rename is_buy -> side, entry_px -> price, entry_sx -> size
    df['side'] = df['is_buy'].map(lambda x: 'bid' if x == 1 else 'ask')
    df = df.drop(columns=['is_buy'])
    df = df.rename(columns={'entry_px': 'price', 'entry_sx': 'size'})

    df = df.reset_index(drop=True)

    return df


def get_snapshot_ts(df: pd.DataFrame) -> Optional[List]:
    snaps = df[df.update_type == 'SNAPSHOT']
    if len(snaps) == 0:
        return None
    return list(snaps['timestamp'].unique())


def starts_with_snapshot(df: pd.DataFrame) -> bool:
    if len(df) == 0:
        return False
    return df.iloc[0]['update_type'] == 'SNAPSHOT'


def remove_snap(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['update_type'] != 'SNAPSHOT']


# this assumes 1 snapshot in DF
def get_snapshot_depth(df: pd.DataFrame) -> Tuple[int, int]:
    return len(df[(df['update_type'] == 'SNAPSHOT') & (df['side'] == 'bid')]), \
            len(df[(df['update_type'] == 'SNAPSHOT') & (df['side'] == 'ask')])
