from pathlib import Path

import awswrangler as wr
import pandas as pd
import boto3
from cache_df import CacheDF
import functools
from typing import List, Tuple
import utils.concurrency.concurrency_utils as cu
from utils.s3.s3_utils import get_session


def load_df(path: str) -> pd.DataFrame:
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
    return wr.s3.read_parquet(path=prefix, path_suffix=suffix, dataset=True, boto3_session=session)


def load_dfs(paths: List[str]) -> List[pd.DataFrame]:
    callables = [functools.partial(load_df, path=path) for path in paths]
    return cu.run_concurrently(callables)


# TODO make default global cache dir
def load_and_cache(files: List[str], cache_dir: str) -> List[pd.DataFrame]:
    print(f'Loading {len(files)} dfs...')
    # check cache first
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    # TODO use joblib.Memory instead
    cache = CacheDF(cache_dir=cache_dir)
    dfs = []
    cached_paths = []
    for path in files:
        hashed_path = str(hash(path))  # can't use s3:// strings as keys, cache_df lib flips out
        if cache.is_cached(hashed_path):
            dfs.append(cache.read(hashed_path))
            cached_paths.append(path)
    print(f'Loaded {len(cached_paths)} cached dfs')
    if len(cached_paths) != len(files):
        to_load_paths = list(set(files) - set(cached_paths))
        loaded = load_dfs(to_load_paths)
        # cache loaded dfs
        for i in range(len(to_load_paths)):
            cache.cache(loaded[i], str(hash(to_load_paths[i])))
        dfs.extend(loaded)
        print(f'Loaded and cached {len(loaded)} dfs')

    return dfs


def sub_df(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    # includes end
    return df[start: end + 1].reset_index(drop=True)


def concat(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    return pd.concat(dfs, ignore_index=True)


def time_range(df: pd.DataFrame) -> Tuple[float, int, int]:
    # time between start and finish
    start = df.iloc[0].timestamp
    end = df.iloc[-1].timestamp

    return end - start, start, end


def get_num_rows(df: pd.DataFrame) -> int:
    return len(df.index)


def get_size_kb(df: pd.DataFrame) -> int:
    return int(df.memory_usage(index=True, deep=True).sum()/1000.0)


def get_time_diff(df1: pd.DataFrame, df2: pd.DataFrame) -> float:
    if df1 is None or df2 is None:
        return 0
    start1 = df1.iloc[0].timestamp
    start2 = df2.iloc[0].timestamp
    return start1 - start2

