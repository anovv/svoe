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
    path = input_item['path']
    # TODO use https://github.com/aio-libs/aiobotocore
    # example https://gist.github.com/mattwang44/0c2e0e244b9e5f901f3881d5f1e85d3a
    df = s3_utils.load_df(path)
    stats.inc_counter.remote(DOWNLOAD_TASKS_FINISHED)
    return df


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def index_df(df: pd.DataFrame, input_item: InputItem, stats: Stats) -> IndexItem:
    stats.inc_counter.remote(INDEX_TASKS_STARTED)
    res = _index_df(df, input_item)
    stats.inc_counter.remote(INDEX_TASKS_FINISHED)
    return res


def _index_df(df: pd.DataFrame, input_item: InputItem) -> IndexItem:
    path = input_item['path']
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

    return index_item
