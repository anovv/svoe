import awswrangler as wr

import utils.concurrency.concurrency_utils as cu
import boto3
import functools
from typing import Tuple, List, Any, Optional, Generator
import pandas as pd
import os

# _sessions_per_process = {}
# _lock = threading.Lock()


# def get_session():
#     # thread safe singleton
#     global _sessions_per_process, _lock
#     pid = os.getpid()
#     if pid not in _sessions_per_process:
#         with _lock:
#             _sessions_per_process[pid] = boto3.Session()
#     return _sessions_per_process[pid]


# TODO set up via env vars
# TODO improve perf, make thread-safe
# https://emasquil.github.io/posts/multithreading-boto3/
def get_session() -> boto3.Session:
    return boto3.session.Session()


def get_file_size_kb(path: str) -> int:
    bucket_name, key = to_bucket_and_key(path)
    session = get_session()
    s3_resource = session.resource('s3')
    # TODO use client.head_object
    obj = s3_resource.Object(bucket_name, key)
    # obj = client.get_object(Bucket=bucket_name, Key=key)
    # more metadata is stored in object
    file_size = obj.content_length

    return int(file_size/1000.0)


def get_file_sizes_kb(paths: List[str]) -> List[int]:
    callables = [functools.partial(get_file_size_kb, path=path) for path in paths]
    return cu.run_concurrently(callables)


def to_bucket_and_key(path: str) -> Tuple[str, str]:
    # 's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-06-11/compaction=raw/version=testing /file.gz.parquet'
    path = path.removeprefix('s3://')
    split = path.split('/')
    bucket_name = split[0]
    key = path.removeprefix(bucket_name + '/')
    return bucket_name, key


def list_files_and_sizes_kb(bucket_name: str, prefix: str = '', page_size: int = 1000, max_items: Optional[int] = None) -> List[Tuple[str, int]]:
    session = get_session()
    client = session.client('s3')
    paginator = client.get_paginator('list_objects') # TODO use list_objects_v2
    pagination_config = {'PageSize': page_size}
    if max_items:
        pagination_config['MaxItems'] = max_items
    iterator = paginator.paginate(
        Bucket=bucket_name,
        PaginationConfig=pagination_config,
        Prefix=prefix
    ) # TODO figure out Delimiter?

    res = []
    for obj in iterator:
        fetched = obj['Contents']
        keys_and_sizes = [(f['Key'], f['Size']/1024) for f in fetched]
        # filter names that match prefix
        res.extend(list(filter(lambda e: e[0] != prefix, keys_and_sizes)))
    return res


def delete_files(bucket_name: str, paths: List[str]):
    if len(paths) > 1000:
        # TODO implemet concurrent delete if > 1000 objects
        # https://boto3.amazonaws.com/v1/documentation/api/1.19.0/guide/clients.html#general-example
        raise ValueError('Can not delete more than 1000 objects from S3, make concurrent requests')

    session = get_session()
    client = session.client('s3')
    client.delete_objects(
        Bucket=bucket_name,
        Delete={'Objects': list(map(lambda path: {'Key': to_bucket_and_key(path)[1]}, paths))}
    )


def inventory() -> Generator[pd.DataFrame, None, None]:
    # TODO implement large files download with progress callback and fetch directly from s3
    inventory_files_folder = '/Users/anov/IdeaProjects/svoe/utils/s3/s3_svoe.test.1_inventory'
    files = os.listdir(inventory_files_folder)
    for f in files:
        yield pd.read_parquet(f'{inventory_files_folder}/{f}')

# for progress bar https://github.com/alphatwirl/atpbar
# https://leimao.github.io/blog/Python-tqdm-Multiprocessing/
