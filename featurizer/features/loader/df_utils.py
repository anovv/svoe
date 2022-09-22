import awswrangler as wr
import pandas as pd
import concurrent.futures
import asyncio
import functools
from typing import List, Tuple


def load_single_file(path: str) -> pd.DataFrame:
    # split path into prefix and suffix
    # this is needed because if dataset=True data wrangler handles input path as a glob pattern,
    # hence messing up special characters
    split = path.split('/')
    suffix = split[len(split) - 1]
    prefix = path.removesuffix(suffix)
    return wr.s3.read_parquet(path=prefix, path_suffix=suffix, dataset=True)


def load_files(paths: List[str]) -> List[pd.DataFrame]:
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1024)
    loop = asyncio.new_event_loop()
    futures = [loop.run_in_executor(executor, functools.partial(load_single_file, path=path)) for path in paths]
    gathered = asyncio.gather(*futures, loop=loop, return_exceptions=True)
    loop.run_until_complete(gathered)
    dfs = []
    for f in futures:
        dfs.append(f.result())
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


def get_len(df: pd.DataFrame) -> int:
    return len(df.index)


def get_size_bytes(df: pd.DataFrame) -> int:
    return df.memory_usage(index=True).sum()


def get_time_diff(df1: pd.DataFrame, df2: pd.DataFrame) -> float:
    if df1 is None or df2 is None:
        return 0
    start1 = df1.iloc[0].timestamp
    start2 = df2.iloc[0].timestamp
    return start1 - start2

