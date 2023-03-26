import json
import time
from typing import Optional, Dict

import featurizer.features.loader.l2_snapshot_utils as l2_utils

import pandas as pd
from ray.util.client import ray

from data_catalog.indexer.models import InputItem, IndexItem
from data_catalog.utils.register import report_stats_decor, EventType
from utils.pandas import df_utils


# TODO set resources
# TODO util this
@ray.remote
def gather_and_wait(args):
    return ray.get(args)


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.SCHEDULED, EventType.STARTED, EventType.FINISHED])
def load_df(input_item: InputItem, stats: 'Stats', task_id: str, extra: Optional[Dict] = None) -> pd.DataFrame:
    path = input_item['path']
    return df_utils.load_df(path)


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.SCHEDULED, EventType.STARTED, EventType.FINISHED])
def index_df(df: pd.DataFrame, input_item: InputItem, stats: 'Stats', task_id: str, extra: Optional[Dict] = None) -> IndexItem:
    return _index_df(df, input_item)


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
                'snapshot_ts': snapshot_ts
            }
            index_item['meta'] = json.dumps(meta)

    return index_item