import hashlib
import time
from pathlib import Path

import awswrangler as wr
import joblib
import pandas as pd
from cache_df import CacheDF
import functools
from typing import List, Tuple, Generator, Optional, Callable

from matplotlib import pyplot as plt

import common.concurrency.concurrency_utils as cu
from common.s3.s3_utils import get_session

CACHE_DIR = '/tmp/svoe/dfs_cache/'


def store_df(path: str, df: pd.DataFrame, cache_dir: str = CACHE_DIR):
    # TODO add caching
    session = get_session()
    wr.s3.to_parquet(df, path=path, dataset=False, compression='gzip', boto3_session=session)


def load_df(path: str, use_cache: bool = True, cache_dir: str = CACHE_DIR) -> pd.DataFrame:
    # caching first
    cache_key = joblib.hash(path) # can't use s3:// strings as keys, cache_df lib flips out
    if use_cache:
        df = get_cached_df(cache_key, cache_dir=cache_dir)
        if df is not None:
            return df


    # split path into prefix and suffix
    # this is needed because if dataset=True data wrangler handles input path as a glob pattern,
    # hence messing up special characters

    # for Python < 3.9
    # def remove_suffix(input_string, suffix):
    #     if suffix and input_string.endswith(suffix):
    #         return input_string[:-len(suffix)]
    #     return input_string

    split = path.split('/')
    suffix = split[len(split) - 1]
    # prefix = remove_suffix(path, suffix)
    prefix = path.removesuffix(suffix)
    session = get_session()
    if '.csv' in path:
        df = wr.s3.read_csv(path=prefix, path_suffix=suffix, dataset=False, boto3_session=session, delimiter=';')
    elif '.parquet' in path:
        df = wr.s3.read_parquet(path=prefix, path_suffix=suffix, dataset=False, boto3_session=session)
    else:
        raise ValueError(f'Unknown file extension: {path}')

    if use_cache:
        cache_df_if_needed(df, cache_key, cache_dir=cache_dir)
    return df


def cache_df_if_needed(df: pd.DataFrame, cache_key: str, cache_dir: str = CACHE_DIR):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    cache = CacheDF(cache_dir=cache_dir)
    if not cache.is_cached(cache_key):
        cache.cache(df, cache_key)


def get_cached_df(cache_key: str, cache_dir: str = CACHE_DIR) -> Optional[pd.DataFrame]:
    try:
        cache = CacheDF(cache_dir=cache_dir)
        if cache.is_cached(cache_key):
            return cache.read(cache_key)
    except:
        print('Exception reading df from cache, clearing...')
        # corrupt cache most likely
        delete_cached_df(cache_key, cache_dir=cache_dir)
    return None


def delete_cached_df(cache_key: str, cache_dir: str = CACHE_DIR):
    cache = CacheDF(cache_dir=cache_dir)
    cache.uncache(cache_key)


def load_dfs(paths: List[str], use_cache: bool = True, cache_dir: str = CACHE_DIR) -> List[pd.DataFrame]:
    callables = [functools.partial(load_df, path=path, use_cache=use_cache, cache_dir=cache_dir) for path in paths]
    return cu.run_concurrently(callables)


def sub_df(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    # includes end
    return df[start: end + 1].reset_index(drop=True)


def sub_df_ts(df: pd.DataFrame, start_ts: float, end_ts: float) -> pd.DataFrame:
    res = df[df['timestamp'].between(start_ts, end_ts, inclusive='both')]
    if len(res) == 0:
        raise ValueError(f'Can not find intersection: {start_ts}, {end_ts}, {df}')
    return res


def concat(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    return pd.concat(dfs, ignore_index=True)


def time_range(df: pd.DataFrame) -> Tuple[float, float, float]:
    # time between start and finish
    start = df.iloc[0].timestamp
    end = df.iloc[-1].timestamp

    return end - start, start, end


def get_num_rows(df: pd.DataFrame) -> int:
    return len(df.index)


# TODO this takes 10s on 5Gb dataframe
def get_size_kb(df: pd.DataFrame) -> int:
    return int(df.memory_usage(index=True, deep=True).sum()/1024.0)


def get_time_diff(df1: pd.DataFrame, df2: pd.DataFrame) -> float:
    if df1 is None or df2 is None:
        return 0
    start1 = df1.iloc[0].timestamp
    start2 = df2.iloc[0].timestamp
    return start1 - start2


def is_ts_sorted(df: pd.DataFrame) -> bool:
    return df['timestamp'].is_monotonic_increasing


def sort_dfs(dfs: List[pd.DataFrame]) -> List[pd.DataFrame]:
    def compare(df1, df2):
        if len(df1) == 0:
            return -1
        if len(df2) == 0:
            return 1
        return int(float(df1.iloc[0]['timestamp']) - float(df2.iloc[0]['timestamp']))

    return sorted(dfs, key=functools.cmp_to_key(compare))


def plot_multi(col_names: List[str], df: pd.DataFrame):
    fig, axes = plt.subplots(nrows=len(col_names), ncols=1)
    for i in range(len(col_names)):
        df.plot(x='timestamp', y=col_names[i], ax=axes[i])
    plt.show()


# TODO typing
def gen_split_df_by_mem(df: pd.DataFrame, chunk_size_kb: int, callback: Optional[Callable] = None) -> Generator:
    # split only ts sorted dfs
    if not is_ts_sorted(df):
        raise ValueError('Only ts-sorted dfs can be split')

    num_rows = len(df)
    df_size_kb = get_size_kb(df)

    if chunk_size_kb > df_size_kb:
        raise ValueError(f'Chunk size {chunk_size_kb}kb is larger then df size {df_size_kb}kb')

    row_size_kb = df_size_kb/num_rows

    chunk_num_rows = int(chunk_size_kb/row_size_kb)

    start = 0
    while start < num_rows:
        t = time.time()
        end = min(start + chunk_num_rows, num_rows) - 1
        # move end while we have same ts to make sure we don't split it
        end_ts = df.iloc[end]['timestamp']
        while end < num_rows and df.iloc[end]['timestamp'] == end_ts:
            end += 1
        yield df.iloc[start: end]
        callback(None, time.time() - t)
        start = end

        # TODO return num splits?


def hash_df(df: pd.DataFrame) -> str:
    return hashlib.sha1(pd.util.hash_pandas_object(df).values).hexdigest()


# assumes uniformly distributed time points
def downsample_uniform(df: pd.DataFrame, every_n_row: int) -> pd.DataFrame:
    return df.iloc[::every_n_row]

