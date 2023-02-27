import json

import featurizer.features.loader.l2_snapshot_utils as l2_utils

import pandas as pd
from ray.util.client import ray

from data_catalog.indexer.actors.stats import Stats, INDEX_TASKS_STARTED, INDEX_TASKS_FINISHED, DOWNLOAD_TASKS_FINISHED, \
    DOWNLOAD_TASKS_STARTED
from data_catalog.indexer.models import InputItem, IndexItem
from utils.pandas import df_utils
from utils.s3 import s3_utils


# TODO set resources
@ray.remote
def gather_and_wait(args):
    return ray.get(args)


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def load_df(input_item: InputItem, stats: Stats) -> pd.DataFrame:
    stats.inc_counter.remote(DOWNLOAD_TASKS_STARTED)
    print(input_item)
    path = input_item['path']
    print(f'Loading {path}...')
    df = s3_utils.load_df(path)
    print(f'Loaded {path}')
    stats.inc_counter.remote(DOWNLOAD_TASKS_FINISHED)
    return df


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def index_df(df: pd.DataFrame, input_item: InputItem, stats: Stats) -> IndexItem:
    stats.inc_counter.remote(INDEX_TASKS_STARTED)
    res = _index_df(df, input_item)
    stats.inc_counter.remote(INDEX_TASKS_FINISHED)
    return res

# TODO s3://svoe.test.1/data_lake/BINANCE/l2_book/BTC-USDT/date=2021-12-22/version=local/BINANCE-l2_book-BTC-USDT-1640194760.230347-34631b91ea284ca2857f9b3938101121.gz.parquet
# debug IndexError: single positional indexer is out-of-bounds in l2_utils.get_snapshot_ts(df)
def _index_df(df: pd.DataFrame, input_item: InputItem) -> IndexItem:
    path = input_item['path']
    print(f'Indexing {path}...')
    index_item = input_item.copy()
    _time_range = df_utils.time_range(df)

    # TODO sync keys with DataCatalog sql model
    index_item.update({
        'start_ts': _time_range[1],
        'end_ts': _time_range[2],
        'size_in_memory_kb': df_utils.get_size_kb(df),
        'num_rows': df_utils.get_num_rows(df),
    })
    if index_item['data_type'] == 'l2_book':
        snapshot_ts = l2_utils.get_snapshot_ts(df)
        if snapshot_ts is not None:
            meta = {
                'snapshot_ts': l2_utils.get_snapshot_ts(df)
            }
            index_item['meta'] = json.dumps(meta)

    print(f'Indexed {path}...')

    return index_item
