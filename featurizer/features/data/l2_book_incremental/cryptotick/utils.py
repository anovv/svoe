from typing import Optional, List, Tuple

import pandas as pd


# see https://www.cryptotick.com/Faq
def preprocess_l2_inc_df(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    # date_str = '20230201'
    datetime_str = f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} '  # yyyy-mm-dd + ' ' (empty SPACE)
    df['time_exchange'] = datetime_str + df['time_exchange']
    df['time_coinapi'] = datetime_str + df['time_coinapi']
    # https://stackoverflow.com/questions/54313463/pandas-datetime-to-unix-timestamp-seconds
    df['timestamp'] = pd.to_datetime(df['time_exchange']).astype(int) / 10 ** 9
    df['receipt_timestamp'] = pd.to_datetime(df['time_coinapi']).astype(int) / 10 ** 9

    # TODO for some reason raw crypottick dates are not sorted
    df.sort_values(by=['timestamp'], ignore_index=True, inplace=True)
    if not df['timestamp'].is_monotonic_increasing:
        raise ValueError('Unable to sort df by timestamp')

    df.drop(columns=['time_exchange', 'time_coinapi'], inplace=True)

    # cryptotick l2_inc should not contain any order_id info
    if pd.notna(df['order_id']).sum() != 0:
        raise ValueError('Cryptotick l2_inc df should not contain order_id values')

    df.drop(columns=['order_id'], inplace=True)

    # rename is_buy -> side, entry_px -> price, entry_sx -> size
    df['side'] = df['is_buy'].map(lambda x: 'bid' if x == 1 else 'ask')
    df.drop(columns=['is_buy'], inplace=True)
    df.rename(columns={'entry_px': 'price', 'entry_sx': 'size'}, inplace=True)

    df.reset_index(drop=True, inplace=True)

    return df


def get_snapshot_ts(df: pd.DataFrame) -> Optional[List]:
    snaps = df[df.update_type == 'SNAPSHOT']
    if len(snaps) == 0:
        return None
    return list(snaps.time_exchange.unique())


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
