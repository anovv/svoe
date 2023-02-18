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
def load_df(input_item: InputItem) -> pd.DataFrame:
    path = input_item['path']
    print(f'Loading {path}...')
    df = s3_utils.load_df(path)
    print(f'Loaded {path}')
    return df


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def index_df(df: pd.DataFrame, input_item: InputItem) -> IndexItem:
    return _index_df(df, input_item)


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
        meta = {
            'snapshot_ts': l2_utils.get_snapshot_ts(df)
        }
        index_item['meta'] = json.dumps(meta)

    print(f'Indexed {path}...')

    return index_item
