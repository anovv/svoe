
import featurizer.features.loader.concurrency_utils as cu
import boto3
import functools
import threading
import os
from typing import Tuple, List
from prefect_aws.credentials import AwsCredentials

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


def get_file_size_kb(path: str, credentials: AwsCredentials = None) -> int:
    # TODO set up via env vars
    # TODO improve perf, make thread-safe
    # https://emasquil.github.io/posts/multithreading-boto3/
    bucket_name, key = _parse_path(path)
    if credentials is not None:
        session = credentials.get_boto3_session()
    else:
        session = boto3.session.Session()

    s3_resource = session.resource('s3')
    obj = s3_resource.Object(bucket_name, key)
    # obj = client.get_object(Bucket=bucket_name, Key=key)
    # more metadata is stored in object
    file_size = obj.content_length

    return int(file_size/1000.0)


def get_file_sizes_kb(paths: List[str]) -> List[int]:
    callables = [functools.partial(get_file_size_kb, path=path) for path in paths]
    return cu.run_concurrently(callables)


def _parse_path(path: str) -> Tuple[str, str]:
    # 's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-06-11/compaction=raw/version=testing /file.gz.parquet'
    path = path.removeprefix('s3://')
    split = path.split('/')
    bucket_name = split[0]
    key = path.removeprefix(bucket_name + '/')
    return bucket_name, key
