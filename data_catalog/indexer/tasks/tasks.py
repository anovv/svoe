import json

import featurizer.features.loader.l2_snapshot_utils as l2_utils
from typing import List

import pandas as pd
from ray.util.client import ray

from data_catalog.indexer.actors.queues import StoreQueue
from data_catalog.indexer.models import InputItem, IndexItem
from utils.pandas import df_utils
from utils.s3 import s3_utils


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def load_and_queue_df(input_item: InputItem, index_queue: List):
    df = ray.get(_load_df.remote(input_item['path']))
    path = input_item['path']
    print(f'Loaded {path}')
    index_queue.append((df, input))


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def _load_df(path: str) -> pd.DataFrame:
    return s3_utils.load_df(path)


# TODO add batching?
# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def index_and_queue_df(df: pd.DataFrame, input_item: InputItem, store_queue: StoreQueue):
    # index_item = ray.get(_index_df.remote(df, input_item))
    # fire and forget
    index_item = _index_df(df, input_item)
    path = input_item['path']
    print(f'Indexed {path}')
    store_queue.put.remote(index_item)


# TODO set CPU=0, set memory and object_store_memory
# @ray.remote
def _index_df(df: pd.DataFrame, input_item: InputItem) -> IndexItem:
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
        meta = {
            'snapshot_ts': l2_utils.get_snapshot_ts(df)
        }
        index_item['meta'] = json.dumps(meta)

    return index_item
