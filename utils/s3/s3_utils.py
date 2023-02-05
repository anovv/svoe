
import utils.concurrency.concurrency_utils as cu
import boto3
import functools
from typing import Tuple, List, Any
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


# TODO set up via env vars
# TODO improve perf, make thread-safe
# https://emasquil.github.io/posts/multithreading-boto3/
def _get_session() -> boto3.Session:
    return boto3.session.Session()

def get_file_size_kb(path: str) -> int:
    bucket_name, key = _parse_path(path)
    session = _get_session()
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

# TODO asyncify paginator https://gist.github.com/gudgud96/bdde37c9cc6b56a88ae3a7a0a217a723
# TODO multithreaded version https://gist.github.com/sjakthol/19367500519a8828ec77ef5d34b1b0b9
# TODO for threaded delete https://gist.github.com/angrychimp/76b8fe9f15c88d7f121db1cc5d2c215d
# TODO retriving common prefixes https://stackoverflow.com/questions/36991468/how-to-retrieve-bucket-prefixes-in-a-filesystem-style-using-boto3
# TODO parallel list https://joshua-robinson.medium.com/listing-67-billion-objects-in-1-bucket-806e4895130f
# TODO more https://gist.github.com/joshuarobinson/ecf4f82e5d935f841b94b8cccae7c990
# https://alukach.com/posts/tips-for-working-with-a-large-number-of-files-in-s3/

# for s3 inventory
# https://gist.github.com/alukach/1a2b8b6366410fb94fa5cee7f72ee304
# https://alukach.com/posts/parsing-s3-inventory-output/
def list_files(bucket_name: str) -> List[Any]:
    session = _get_session()
    client = session.client('s3')
    paginator = client.get_paginator('list_objects')
    iterator = paginator.paginate(
        Bucket=bucket_name,
        PaginationConfig={'MaxItems': 10, 'PageSize': 5}
    ) # TODO set Delimiter?

    # res = []
    # for obj in iterator:
    #     res.append(obj)
    # return res
    print(next(iter(iterator)))



