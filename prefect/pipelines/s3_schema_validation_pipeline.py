from functools import reduce

import prefect
from prefect import task, Flow
from prefect.tasks.aws.s3 import S3List
from numpy import dtype
from typing import Tuple, List, Dict
from prefect.client.secrets import Secret
from fastparquet import ParquetFile
import s3fs

s3fs.S3FileSystem.cachable = False
# s3 = s3fs.S3FileSystem(key=Secret('AWS_KEY').get(), secret=Secret('AWS_SECRET').get())
s3 = s3fs.S3FileSystem()

S3_BUCKET = 'svoe.test.1'

# valid schemas
TICKER_SCHEMA = {}
L2_BOOK_SCHEMA = {
    'timestamp':  dtype('float64'),
    'receipt_timestamp': dtype('float64'),
    'delta': dtype('bool'),
    'side': dtype('O'),
    'price': dtype('float64'),
    'size': dtype('float64')
}
L3_BOOK_SCHEMA = {}
TRADES_SCHEMA = {}
OPEN_INTEREST_SCHEMA = {}
FUNDING_SCHEMA = {}
LIQUIDATIONS_SCHEMA = {}

# sample files
# 'svoe.test.1/parquet/BINANCE/l2_book/XVS-USDT/BINANCE-l2_book-XVS-USDT-1617702408.parquet' - delta - float
#
# svoe.test.1/parquet/BINANCE_FUTURES/l2_book/ADA-USDT/BINANCE_FUTURES-l2_book-ADA-USDT-1626162558.parquet - delta - str
#
# 'svoe.test.1/parquet/FTX/l2_book/BNB-USD/FTX-l2_book-BNB-USD-1626162563.parquet
#
# svoe.test.1/parquet/BINANCE/l2_book/BTC-USDT/BINANCE-l2_book-BTC-USDT-1625909429.parquet
#
# svoe.test.1/parquet/BINANCE_FUTURES/liquidations/ADA-USDT/BINANCE_FUTURES-liquidations-ADA-USDT-1625757954.parquet

@task
def list_files() -> List[str]: #TODO param prefix
    # should have one file
    # ['parquet/BINANCE/l2_book/XVS-USDT/BINANCE-l2_book-XVS-USDT-1617702408.parquet']
    list = S3List(bucket=S3_BUCKET)
    # return list.run(prefix='parquet/BINANCE/l2_book/XVS-USDT')
    return list.run(prefix='parquet/FTX/l2_book/UNI-USD')

@task
def validate_schema(file_path) -> Tuple[bool, str]:
    logger = prefect.context.get('logger')
    # s3://svoe.test.1/parquet/BINANCE/l2_book/XVS-USDT/BINANCE-l2_book-XVS-USDT-1617702408.parquet
    full_path = 's3://' + str(S3_BUCKET) + '/' + file_path
    logger.info('Validating schema for ' + str(full_path))
    pf = ParquetFile(full_path, open_with=s3.open)
    data_types = pf.dtypes
    if L2_BOOK_SCHEMA.keys() != data_types.keys():
        return False, 'Keys mismatch: ' + str(L2_BOOK_SCHEMA.keys() - data_types.keys())

    for key, value in L2_BOOK_SCHEMA.items():
        if data_types[key] != value:
            return False, 'Type mismatch for key ' + str(key) + ' Expected ' + str(value) + ' Got ' + str(data_types[key])

    return True, 'Ok'

@task
def reduce_tuples(tuples):
    # return reduce(lambda res, tuple: res[tuple[1]] if tuple[1] in res else {}, tuples, {})
    res = {}
    for tuple in tuples:
        if tuple[1] in res:
            res[tuple[1]] += 1
        else:
            res[tuple[1]] = 1

    logger = prefect.context.get('logger')
    logger.info("Result " + str(res))
    return res

with Flow('schema_validation') as flow:
    files = list_files()
    mapped_res = validate_schema.map(files)
    res = reduce_tuples(mapped_res)

flow.run()


