import tempfile
from pathlib import Path

import s3fs

import common.concurrency.concurrency_utils as cu
import boto3
import functools
from typing import Tuple, List, Optional, Generator
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


def delete_by_prefix(bucket_name: str, prefix: str):
    s3 = s3fs.S3FileSystem() # TODO init in container?
    s3.rm(bucket_name + '/' + prefix)


def upload_dir(s3_path: str, local_path: str):
    s3 = s3fs.S3FileSystem() # TODO init in container?
    s3.put(local_path, s3_path, recursive=True)


def download_dir(s3_path: str) -> Tuple[tempfile.TemporaryDirectory, List[str]]:
    s3 = s3fs.S3FileSystem()  # TODO init in container?
    files = s3.ls(s3_path) # removes 's3://' prefix
    s3_path_no_pref = s3_path.removeprefix('s3://')

    temp_dir = tempfile.TemporaryDirectory()
    paths = [f'{temp_dir.name}/{f.removeprefix(s3_path_no_pref)}' for f in files]
    # TODO asyncify/multithread
    for i in range(len(files)):
        s3.download(files[i], paths[i])

    return temp_dir, paths


def download_file(s3_path) -> Tuple[tempfile.TemporaryDirectory, str]:
    s3 = s3fs.S3FileSystem()
    temp_dir = tempfile.TemporaryDirectory()
    bucket, key = to_bucket_and_key(s3_path)
    fname = Path(key).name
    path = f'{temp_dir.name}/{fname}'
    s3.download(f'{bucket}/{key}', path)
    return temp_dir, path



def inventory() -> Generator[pd.DataFrame, None, None]:
    # TODO implement large files download with progress callback and fetch directly from s3
    inventory_files_folder = '/Users/anov/IdeaProjects/svoe/utils/s3/s3_svoe.test.1_inventory'
    files = os.listdir(inventory_files_folder)
    for f in files:
        yield pd.read_parquet(f'{inventory_files_folder}/{f}')

# for progress bar https://github.com/alphatwirl/atpbar
# https://leimao.github.io/blog/Python-tqdm-Multiprocessing/
