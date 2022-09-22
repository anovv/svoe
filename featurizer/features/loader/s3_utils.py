
import featurizer.features.loader.concurrency_utils as cu
import boto3
import functools
from typing import Tuple, List


def get_file_size_kb(path: str) -> int:
    # TODO set up via env vars
    s3 = boto3.resource('s3')
    bucket_name, key = _parse_path(path)
    obj = s3.Object(bucket_name, key)
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
