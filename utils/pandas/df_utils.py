from pathlib import Path

import awswrangler as wr
import pandas as pd
from cache_df import CacheDF
import functools
from typing import List, Tuple
import utils.concurrency.concurrency_utils as cu
from utils.s3.s3_utils import get_session
from joblib import hash

CACHE_DIR = '/tmp/svoe/dfs_cache/'


def load_df(path: str, use_cache: bool = True, cache_dir: str = CACHE_DIR) -> pd.DataFrame:
    # caching first
    cache_key = str(hash(path)) # can't use s3:// strings as keys, cache_df lib flips out
    if use_cache:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        # TODO use joblib.Memory instead ?
        cache = CacheDF(cache_dir=cache_dir)
        if cache.is_cached(cache_key):
            return cache.read(cache_key)

    # split path into prefix and suffix
    # this is needed because if dataset=True data wrangler handles input path as a glob pattern,
    # hence messing up special characters

    # for Python < 3.9
    def remove_suffix(input_string, suffix):
        if suffix and input_string.endswith(suffix):
            return input_string[:-len(suffix)]
        return input_string

    split = path.split('/')
    suffix = split[len(split) - 1]
    prefix = remove_suffix(path, suffix)
    session = get_session()
    df = wr.s3.read_parquet(path=prefix, path_suffix=suffix, dataset=True, boto3_session=session)

    if use_cache:
        cache = CacheDF(cache_dir=cache_dir)
        if not cache.is_cached(cache_key):
            cache.cache(df, cache_key)
    return df


def load_dfs(paths: List[str], use_cache: bool = True, cache_dir: str = CACHE_DIR) -> List[pd.DataFrame]:
    callables = [functools.partial(load_df, path=path, use_cache=use_cache, cache_dir=cache_dir) for path in paths]
    return cu.run_concurrently(callables)


def sub_df(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    # includes end
    return df[start: end + 1].reset_index(drop=True)


def sub_df_ts(df: pd.DataFrame, start_ts: float, end_ts: float) -> pd.DataFrame:
    return df[df['timestamp'].between(start_ts, end_ts,inclusive='both')]


def concat(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    return pd.concat(dfs, ignore_index=True)


def time_range(df: pd.DataFrame) -> Tuple[float, float, float]:
    # time between start and finish
    start = df.iloc[0].timestamp
    end = df.iloc[-1].timestamp

    return end - start, start, end


def get_num_rows(df: pd.DataFrame) -> int:
    return len(df.index)


def get_size_kb(df: pd.DataFrame) -> int:
    return int(df.memory_usage(index=True, deep=True).sum()/1024.0)


def get_time_diff(df1: pd.DataFrame, df2: pd.DataFrame) -> float:
    if df1 is None or df2 is None:
        return 0
    start1 = df1.iloc[0].timestamp
    start2 = df2.iloc[0].timestamp
    return start1 - start2

