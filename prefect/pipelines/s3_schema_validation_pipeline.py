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

import prefect
from prefect import task, Flow
from prefect.tasks.aws.s3 import S3List
from numpy import dtype
from typing import Tuple, List, Dict
from prefect.client.secrets import Secret
from fastparquet import ParquetFile
import s3fs
from prefect.utilities.debug import raise_on_exception
from enum import Enum

import pyarrow as pa
import pyarrow.parquet as pq

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

class SchemaInconsistency(Enum):
    UNKNOWN = 0 # unknown inconsistency, needs manual research
    # known schema inconsistencies:
    L2_BOOK_CAST_DELTA_FROM_OBJECT_TO_BOOL = 1 # l2 book, 'delta' is Object, should be bool
    L2_BOOK_SWAP_NAMES_RECEIPT_TIMESTAMP_AND_DELTA = 2 # l2 book, 'delta' is float64, 'receipt_timestamp' is bool, field names should be swapped

@task
def list_files() -> List[str]: #TODO param prefix
    # should have one file
    # ['parquet/BINANCE/l2_book/XVS-USDT/BINANCE-l2_book-XVS-USDT-1617702408.parquet']
    # logger = prefect.context.get('logger')
    # logger.info('Secret: ' + Secret('AWS_KEY').get())
    # print('Secret: ' + Secret('AWS_KEY').get())
    list = S3List(bucket=S3_BUCKET)
    # prefix = 'parquet/BINANCE/l2_book/BNB-USDT'
    # prefix = 'parquet/FTX/l2_book/UNI-USD'
    prefix = 'parquet/BINANCE/l2_book/XVS-USDT'
    return list.run


# TODO use awsdatawrangler
@task
def validate_schema(file_path) -> Tuple[str, ParquetFile]:
    logger = prefect.context.get('logger')
    s3fs.S3FileSystem.cachable = False
    s3 = s3fs.S3FileSystem(key=Secret('AWS_KEY').get(), secret=Secret('AWS_SECRET').get())
    full_path = 's3://' + str(S3_BUCKET) + '/' + file_path
    logger.info('Validating schema for ' + str(full_path))
    pf = ParquetFile(full_path, open_with=s3.open)
    data_types = pf.dtypes

    # TODO check for existing inconsistencies

    if L2_BOOK_SCHEMA.keys() != data_types.keys():
        return 'Keys mismatch: ' + str(L2_BOOK_SCHEMA.keys() - data_types.keys()), pf

    for key, value in L2_BOOK_SCHEMA.items():
        if data_types[key] != value:
            return 'Type mismatch for key ' + str(key) + ' Expected ' + str(value) + ' Got ' + str(data_types[key]), pf

    return 'Ok', pf

@task
def update_schema(file_path, inconsistency):
    logger = prefect.context.get('logger')
    s3fs.S3FileSystem.cachable = False
    s3 = s3fs.S3FileSystem(key=Secret('AWS_KEY').get(), secret=Secret('AWS_SECRET').get())
    full_path = 's3://' + str(S3_BUCKET) + '/' + file_path
    logger.info('Updating schema for ' + str(full_path))
    pf = ParquetFile(full_path, open_with=s3.open)
    df = pf.to_pandas()

    if inconsistency == SchemaInconsistency.L2_BOOK_CAST_DELTA_FROM_OBJECT_TO_BOOL:
        df['delta'] = df['delta'].astype('bool')
    if inconsistency == SchemaInconsistency.L2_BOOK_SWAP_NAMES_RECEIPT_TIMESTAMP_AND_DELTA:
        return #TODO

    table = pa.Table.from_pandas(df=df)
    write_path = 's3://svoe.test.1/parquet/test1.parquet' # TODO
    writer = pq.ParquetWriter(write_path, table.schema, compression='BROTLI', compression_level=6) # TODO config this
    writer.write_table(table=table)
    writer.close()

@task
def reduce_tuples(tuples):
    # TODO
    # return reduce(lambda res, tup: (res.update({tup[1]: (res[tup[1]] + 1)}) or res) if tup[1] in res else (res.update({tup[1]: 1}) or res), tuples, {})
    res = {}
    for tup in tuples:
        if not tup:
            continue
        if res.get(tup[1], None):
            res[tup[1]] += 1
        else:
            res[tup[1]] = 1

    return res

with Flow('schema_validation') as flow:
    files = list_files()
    mapped_res = validate_schema.map(files)
    reduce_tuples(mapped_res)

from prefect.executors import DaskExecutor
# executor = DaskExecutor(address=cluster.scheduler_address)
executor = DaskExecutor(address='tcp://13.231.161.223:8786', debug=True)

with raise_on_exception():
    state = flow.run
    # state = flow.run()
    task_ref = flow.get_tasks(name=reduce_tuples.name)[0]
    print(state.result[task_ref].result)

