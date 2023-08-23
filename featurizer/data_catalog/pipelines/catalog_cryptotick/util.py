from typing import Optional

import ciso8601
import pandas as pd

from common.pandas import is_ts_sorted


def process_cryptotick_timestamps(df: pd.DataFrame, date_str: Optional[str] = None) -> pd.DataFrame:
    if date_str is not None:
        # certain data_types from cryptotick (e.g. L2 book) do not include date into time_exchange column (only hours/m/s...)
        # so it needs to be passed from upstream
        # date_str = dd-mm-yyyy '01-02-2023'
        datetime_str = f'{date_str[6:10]}-{date_str[3:5]}-{date_str[0:2]}T'  # yyyy-mm-dd + 'T'
    else:
        datetime_str = ''

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

    return df
