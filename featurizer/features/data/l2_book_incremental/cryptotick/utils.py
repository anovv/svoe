import time
from typing import Optional, List, Tuple, Any

import diskcache
from streamz import Stream

from featurizer.features.data.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd import L2SnapshotFD
from ray_cluster.testing_utils import mock_feature
from utils.pandas.df_utils import is_ts_sorted, concat, gen_split_df_by_mem

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


# splits big L2 inc df into chunks, adding full snapshot to the beginning of each chunk
def split_l2_inc_df_and_pad_with_snapshot(path: str, raw_df: pd.DataFrame, split_size_kb: int, date_str: str) -> List[pd.DataFrame]:
    # TODO move this to load_df?
    print('split started')
    print('preproc started')
    # processed_cache_key = joblib.hash(path + '_processed')
    # df = get_cached_df(processed_cache_key)
    # if df is None:
    #     print('preproc NOT in cache, calculating')
    #     raw_date_str = to_raw(date_str)
    #     df = preprocess_l2_inc_df(raw_df, raw_date_str)
    #     cache_df_if_needed(df, processed_cache_key)
    # else:
    #     print('found cached preproc')

    # DD-MM-YYYY -> YYYYMMDD
    def to_raw_date(d):
        return f'{d[6: 10]}{d[3:5]}{d[0:2]}'
    raw_date_str = to_raw_date(date_str)
    df = preprocess_l2_inc_df(raw_df, raw_date_str)
    # approx_num_split = int(get_size_kb(df)/split_size_kb)
    print('preproc finished')
    gen = gen_split_df_by_mem(df, split_size_kb)
    res = []
    prev_snap = None
    i = 0
    for split in gen:
        # TODO this is for debug
        if i > 2:
            break

        if i > 0:
            split = prepend_snap(split, prev_snap)
        # events_cache_key = joblib.hash(f'{path}_{i}_events')
        snap = run_l2_snapshot_stream(split)
        res.append(split)
        prev_snap = snap
        print(f'split {i} finished')
        i += 1

    print('split finished')

    return res


# TODO typing
def run_l2_snapshot_stream(l2_inc_df: pd.DataFrame, events_cache_key: Optional[str] = None) -> Any:
    print('Parse events started')
    t = time.time()
    # if events_cache_key is not None:
    #     cache = diskcache.Cache('/tmp/svoe/objs_cache/')
    #     events = cache.get(events_cache_key)
    #     if events is None:
    #         print('No parsed events cached, calculating...')
    #         events = CryptotickL2BookIncrementalData.parse_events(l2_inc_df)
    #         cache[events_cache_key] = events
    #     else:
    #         print('Parsed events cached')
    # else:
    #     events = CryptotickL2BookIncrementalData.parse_events(l2_inc_df)

    events = CryptotickL2BookIncrementalData.parse_events(l2_inc_df)
    print(f'Parse events finished: {time.time() - t}s')
    source = Stream()

    # cryptotick stores 5000 depth levels
    depth = 5000
    feature_params = {'dep_schema': 'cryptotick', 'depth': depth, 'sampling': 'skip_all'}
    _, stream_state = L2SnapshotFD.stream({mock_feature(0): source}, feature_params)

    print('Running events started')
    t = time.time()
    for event in events:
        source.emit(event)
    print(f'Running events finished: {time.time() - t}s')

    return L2SnapshotFD._state_snapshot(stream_state, depth)


def prepend_snap(df: pd.DataFrame, snap) -> pd.DataFrame:
    # TODO inc this
    ts = snap['timestamp']
    receipt_ts = snap['receipt_timestamp']

    # make sure start of this block differs from prev
    microsec = 0.000001
    ts += microsec
    receipt_ts += microsec

    if ts >= df.iloc[0]['timestamp'] or receipt_ts >= df.iloc[0]['receipt_timestamp']:
        raise ValueError('Unable to shift snapshot ts when prepending')

    df_bids = pd.DataFrame(snap['bids'], columns=['price', 'size'])
    df_bids['side'] = 'bid'
    df_asks = pd.DataFrame(snap['asks'], columns=['price', 'size'])
    df_asks['side'] = 'ask'
    df_snap = concat([df_bids, df_asks])
    df_snap['update_type'] = 'SNAPSHOT'
    df_snap['timestamp'] = ts
    df_snap['receipt_timestamp'] = receipt_ts

    return concat([df_snap, df])


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
