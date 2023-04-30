import concurrent
import functools
from typing import List, Tuple, Dict

import pandas as pd
import ray

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItem
from data_catalog.common.utils.sql.models import DataCatalog, make_catalog_item
from featurizer.features.data.l2_book_incremental.cryptotick.utils import preprocess_l2_inc_df, \
    gen_split_l2_inc_df_and_pad_with_snapshot
from utils.pandas import df_utils


@ray.remote(num_cpus=0.9, resources={'worker_size_large': 1, 'instance_spot': 1})
def load_split_catalog_store_l2_inc_df(input_item: InputItem, chunk_size_kb: int, date_str: str, db_actor: DbActor) -> Dict:
    print('Load started')
    path = input_item[DataCatalog.path.name]
    df = df_utils.load_df(path)
    print('Load finished')
    print('Preproc started')
    processed_df = preprocess_l2_inc_df(df, date_str)
    print('Preproc finished')
    gen = gen_split_l2_inc_df_and_pad_with_snapshot(processed_df, chunk_size_kb)
    catalog_items = []
    split_id = 0
    num_splits = 0

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    store_futures = []

    print('Split started')
    for split in gen:
        item_split = input_item.copy()

        # additional info to be passed to catalog item
        compaction = f'{chunk_size_kb}kb' if chunk_size_kb < 1024 else f'{round(chunk_size_kb / 1024, 2)}mb'
        item_split[DataCatalog.compaction.name] = compaction
        item_split[DataCatalog.source.name] = 'cryptotick'
        item_split[DataCatalog.extras.name] = {
            'source_path': item_split[DataCatalog.path.name],
            'split_id': split_id,
        }

        # remove raw source path so it is constructed by SqlAlchemy default value when making catalog item
        del item_split[DataCatalog.path.name]

        catalog_item = make_catalog_item(split, item_split)
        store_futures.append(
            executor.submit(functools.partial(store_df, df=split, path=catalog_item.path))
        )

        catalog_items.append(catalog_item)
        split_id += 1
        num_splits += 1

    for catalog_item in catalog_items:
        catalog_item.extras['num_splits'] = num_splits

    print('Split finished')
    concurrent.futures.wait(store_futures)
    print('Store finished')
    res = ray.get(db_actor.write_batch.remote(catalog_items))
    print('Write db finished')
    return res


def store_df(df: pd.DataFrame, path: str):
    print('Store started')
    df_utils.store_df(path, df)
    print(f'Store finished {path}')
