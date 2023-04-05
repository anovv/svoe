from typing import Optional, Dict, List

import joblib
import ray

import pandas as pd

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItem, InputItemBatch
from data_catalog.common.utils.register import report_stats_decor, EventType
from data_catalog.common.utils.sql.models import make_catalog_item, DataCatalog, SVOE_S3_CATALOGED_DATA_BUCKET
from featurizer.features.data.l2_book_incremental.cryptotick.utils import split_l2_inc_df_and_pad_with_snapshot
from utils.pandas import df_utils


# TODO set resources
from utils.pandas.df_utils import get_cached_df, cache_df_if_needed


@ray.remote
def gather_and_wait(args):
    return ray.get(args)


# TODO set resources
# used to pipe dag nodes which outputs do not depend on each other
@ray.remote
def chain_no_ret(*args):
    return args[0]


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.SCHEDULED, EventType.STARTED, EventType.FINISHED])
def load_df(input_item: InputItem, stats: 'Stats', task_id: str, stats_extra: Optional[Dict] = None) -> pd.DataFrame:
    print('load started')
    path = input_item['path']
    # TODO this is for debug
    head = 100000
    head_key = joblib.hash(f'{path}_head_{head}')
    df = get_cached_df(head_key)
    if df is None:
        df = df_utils.load_df(path)
        df = df.head(head) 
        cache_df_if_needed(df, head_key)
    print(input_item['size_kb'])
    print('load finished')
    return df


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.SCHEDULED, EventType.STARTED, EventType.FINISHED])
def catalog_df(df: pd.DataFrame, input_item: InputItem, stats: 'Stats', task_id: str) -> DataCatalog:
    print('catalog_df started')
    item = make_catalog_item(df, input_item)
    print('catalog_df finished')
    return item


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.FINISHED])
def write_batch(db_actor: DbActor, batch: List[DataCatalog], stats: 'Stats', task_id: str) -> Dict:
    return ray.get(db_actor._write_batch.remote(batch))


# TODO we can add actor method ad as DAG node directly https://docs.ray.io/en/latest/ray-core/ray-dag.html#ray-dag-guide
# TODO no need to pass DbActor
# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.FINISHED])
def filter_existing(db_actor: DbActor, input_batch: InputItemBatch, stats: 'Stats', task_id: str) -> InputItemBatch:
    return ray.get(db_actor._filter_batch.remote(input_batch))


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.STARTED, EventType.FINISHED])
def store_df(df: pd.DataFrame, catalog_item: DataCatalog, stats: 'Stats', task_id: str, stats_extra: Optional[Dict] = None):
    print('Store started')
    path = catalog_item.path
    df_utils.store_df(path, df)
    print('Store finished')


@ray.remote
@report_stats_decor([EventType.STARTED, EventType.FINISHED])
def split_l2_inc_df(path: str, df: pd.DataFrame, chunk_size_kb: int, date_str: str, stats: 'Stats', task_id: str) -> List[pd.DataFrame]:
    return split_l2_inc_df_and_pad_with_snapshot(path, df, chunk_size_kb, date_str)

