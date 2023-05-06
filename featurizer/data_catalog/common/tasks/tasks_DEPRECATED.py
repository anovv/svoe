from typing import Optional, Dict, List

import ray

import pandas as pd

from featurizer.data_catalog.common.actors.db import DbActor
from featurizer.data_catalog.common.data_models.models import InputItem, InputItemBatch
from featurizer.data_catalog.common.utils.register import report_stats_decor, EventType
from featurizer.data_catalog.common.sql.models import DataCatalog
from featurizer.data_catalog.pipelines.catalog_cryptotick.tasks import make_catalog_item
from utils.pandas import df_utils


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
    path = input_item[DataCatalog.path.name]
    df = df_utils.load_df(path)
    print('load finished')
    return df


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.STARTED, EventType.FINISHED])
def catalog_df(df: pd.DataFrame, input_item: InputItem, stats: 'Stats', task_id: str) -> DataCatalog:
    print('catalog_df started')
    item = make_catalog_item(df, input_item)
    print('catalog_df finished')
    return item


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.FINISHED])
def write_batch(db_actor: DbActor, batch: List[DataCatalog], stats: 'Stats', task_id: str) -> Dict:
    return ray.get(db_actor.write_batch.remote(batch))


# TODO we can add actor method ad as DAG node directly https://docs.ray.io/en/latest/ray-core/ray-dag.html#ray-dag-guide
# TODO no need to pass DbActor
# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.FINISHED])
def filter_existing(db_actor: DbActor, input_batch: InputItemBatch, stats: 'Stats', task_id: str) -> InputItemBatch:
    return ray.get(db_actor.filter_batch.remote(input_batch))


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.STARTED, EventType.FINISHED])
def store_df(df: pd.DataFrame, catalog_item: DataCatalog, stats: 'Stats', task_id: str, stats_extra: Optional[Dict] = None):
    print('Store started')
    path = catalog_item.path
    # TODO uncomment
    df_utils.store_df(path, df)
    print(f'Store finished {path}')
