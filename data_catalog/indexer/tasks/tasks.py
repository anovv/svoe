import json
import time
from typing import Optional, Dict

import featurizer.features.loader.l2_snapshot_utils as l2_utils

import pandas as pd
from ray.util.client import ray

from data_catalog.indexer.actors.stats import Stats, INDEX_TASKS_STARTED, INDEX_TASKS_FINISHED, DOWNLOAD_TASKS_FINISHED, \
    DOWNLOAD_TASKS_STARTED, DOWNLOAD_TASK_TYPE, INDEX_TASK_TYPE
from data_catalog.indexer.models import InputItem, IndexItem
from utils.pandas import df_utils
from utils.s3 import s3_utils


# TODO set resources
@ray.remote
def gather_and_wait(args):
    return ray.get(args)


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def load_df(input_item: InputItem, stats: Stats, task_id: str, extra: Optional[Dict] = None) -> pd.DataFrame:
    event = {
        'task_id': task_id,
        'event_type': DOWNLOAD_TASKS_STARTED,
        'timestamp': time.time()
    }
    if extra is not None and 'size_kb' in extra:
        event['size_kb'] = extra['size_kb']
    stats.event.remote(DOWNLOAD_TASK_TYPE, event)
    path = input_item['path']
    # TODO use https://github.com/aio-libs/aiobotocore for df download
    # example https://gist.github.com/mattwang44/0c2e0e244b9e5f901f3881d5f1e85d3a
    df = df_utils.load_df(path)
    event['event_type'] = DOWNLOAD_TASKS_FINISHED
    now = time.time()
    event['latency'] = now - event['timestamp']
    event['timestamp'] = now
    stats.event.remote(DOWNLOAD_TASK_TYPE, event)
    return df


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def index_df(df: pd.DataFrame, input_item: InputItem, stats: Stats, task_id: str, extra: Optional[Dict] = None) -> IndexItem:
    event = {
        'task_id': task_id,
        'event_type': INDEX_TASKS_STARTED,
        'timestamp': time.time()
    }
    if extra is not None and 'size_kb' in extra:
        event['size_kb'] = extra['size_kb']
    stats.event.remote(INDEX_TASK_TYPE, event)
    res = _index_df(df, input_item)
    event['event_type'] = INDEX_TASKS_FINISHED
    now = time.time()
    event['latency'] = now - event['timestamp']
    event['timestamp'] = now
    stats.event.remote(INDEX_TASK_TYPE, event)
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
