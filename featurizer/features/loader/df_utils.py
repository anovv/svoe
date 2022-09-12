import awswrangler as wr
import pandas as pd
import concurrent.futures
import asyncio
import functools

def _load_df(paths, nthreads=4):
    return wr.s3.read_parquet(path=paths, use_threads=nthreads)

def _load_dfs_sequential(paths, nthreads=4):
    return wr.s3.read_parquet(path=paths, use_threads=nthreads, chunked=True)

def _load_dfs_concurrent(paths):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1024)
    loop = asyncio.new_event_loop()
    futures = [loop.run_in_executor(executor, functools.partial(_load_df, paths=path, nthreads=1)) for path in paths]
    gathered = asyncio.gather(*futures, loop=loop, return_exceptions=True)
    loop.run_until_complete(gathered)
    dfs = []
    for f in futures:
        dfs.append(f.result())
    return dfs

def _sub_df(df, start, end):
    # includes end
    return df[start: end + 1].reset_index(drop=True)

def _concat(df1, df2):
    return pd.concat([df1, df2], ignore_index=True)

def _time_range(df):
    # time between start and finish
    start = df.iloc[0].timestamp
    end = df.iloc[-1].timestamp

    return end - start, start, end

def _get_len(df):
    return len(df.index)

def _get_size_bytes(df):
    return df.memory_usage(index=True).sum()

def _get_time_diff(df1, df2):
    if df1 is None or df2 is None:
        return 0
    start1 = df1.iloc[0].timestamp
    start2 = df2.iloc[0].timestamp
    return start1 - start2

