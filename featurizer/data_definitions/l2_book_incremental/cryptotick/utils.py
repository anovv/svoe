import time
from typing import Optional, List, Tuple, Any, Generator, Callable

import joblib
from streamz import Stream

from featurizer.data_catalog.pipelines.catalog_cryptotick.util import process_cryptotick_timestamps
from featurizer.data_definitions.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd import L2SnapshotFD
from featurizer.utils.testing_utils import mock_feature
from utils.pandas.df_utils import concat, gen_split_df_by_mem, get_cached_df, load_df, \
    cache_df_if_needed

import pandas as pd


# see https://www.cryptotick.com/Faq
# this is a heavy compute operation, 5Gb df takes 4-5 mins
def preprocess_l2_inc_df(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
    df = process_cryptotick_timestamps(df, date_str)

    # cryptotick l2_inc should not contain any order_id info
    if 'order_id' in df and pd.notna(df['order_id']).sum() != 0:
        raise ValueError('Cryptotick l2_inc df should not contain order_id values')

    if 'order_id' in df:
        df = df.drop(columns=['order_id'])

    # rename is_buy -> side, entry_px -> price, entry_sx -> size
    df['side'] = df['is_buy'].map(lambda x: 'bid' if x == 1 else 'ask')
    df = df.drop(columns=['is_buy'])
    df = df.rename(columns={'entry_px': 'price', 'entry_sx': 'size'})

    df = df.reset_index(drop=True)

    return df


# TODO split_size_kb == 2*1024 results in update_type == SUB not finding price level in a book?
#  same for 512
#  smaller splits seem to also work (1*1024 works)
# splits big L2 inc df into chunks, adding full snapshot to the beginning of each chunk
def gen_split_l2_inc_df_and_pad_with_snapshot(processed_df: pd.DataFrame, split_size_kb: int, callback: Optional[Callable] = None) -> Generator:
    if split_size_kb < 0:
        return [processed_df]

    if callback is None:
        def p(i, t):
            print(f'split {i} finished: {t}s')
        callback = p

    gen = gen_split_df_by_mem(processed_df, split_size_kb)
    prev_snap = None
    i = 0
    for split in gen:
        t = time.time()
        if i > 0:
            split = prepend_snap(split, prev_snap)
        snap = run_l2_snapshot_stream(split)
        yield split
        prev_snap = snap
        callback(i, time.time() - t)
        i += 1


# TODO typing
def run_l2_snapshot_stream(l2_inc_df: pd.DataFrame) -> Any:
    events = CryptotickL2BookIncrementalData.parse_events(l2_inc_df)
    source = Stream()

    # cryptotick stores 5000 depth levels
    depth = 5000
    feature_params = {'dep_schema': 'cryptotick', 'depth': depth, 'sampling': 'skip_all'}
    _, stream_state = L2SnapshotFD.stream({mock_feature(0): source}, feature_params)
    for event in events:
        source.emit(event)

    return L2SnapshotFD._state_snapshot(stream_state, depth)


def prepend_snap(df: pd.DataFrame, snap) -> pd.DataFrame:
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


# Also cached:
# path='s3://svoe-cryptotick-data/limitbook_full/20230202/BINANCE_SPOT_BTC_USDT.csv.gz',
# date_str='02-02-2023'
def mock_processed_cryptotick_df(
    path: str = 's3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz',
    date_str: str = '01-02-2023',
    split_size_kb: int = 100 * 1024
) -> pd.DataFrame:
    print('Loading mock cryptotick df...')
    key_proc = joblib.hash(f'{path}_proc_{split_size_kb}')
    proc_df = get_cached_df(key_proc)
    if proc_df is not None:
        print('Mock cryptotick df cached')
        return proc_df
    raw_df = load_df(path)
    proc_df = preprocess_l2_inc_df(raw_df, date_str)
    if split_size_kb < 0:
        split = proc_df
    else:
        split_gen = gen_split_df_by_mem(proc_df, split_size_kb)
        split = next(split_gen)
    cache_df_if_needed(split, key_proc)
    print('Done loading mock cryptotick df')
    return split


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
