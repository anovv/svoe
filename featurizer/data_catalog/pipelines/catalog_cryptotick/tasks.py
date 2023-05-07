import concurrent
import functools
import time
from datetime import datetime
from typing import Dict, Callable, Optional

import pandas as pd
import pytz
import ray

from featurizer.data_catalog.common.actors.db import DbActor
from featurizer.data_catalog.common.data_models.models import InputItem
from featurizer.data_catalog.common.sql.models import DataCatalog, _construct_s3_path
from featurizer.data_definitions.l2_book_incremental.cryptofeed import utils as cryptofeed_l2_utils
from featurizer.data_definitions.l2_book_incremental.cryptotick import utils as cryptotick_l2_utils
from featurizer.data_definitions.l2_book_incremental.cryptotick.utils import preprocess_l2_inc_df, \
    gen_split_l2_inc_df_and_pad_with_snapshot
from utils.pandas import df_utils



# TODO set cpu separately when running on aws kuber cluster
@ray.remote(num_cpus=2, resources={'worker_size_large': 1, 'instance_spot': 1})
def load_split_catalog_store_l2_inc_df(input_item: InputItem, chunk_size_kb: int, date_str: str, db_actor: DbActor, callback: Optional[Callable] = None) -> Dict:
    path = input_item[DataCatalog.path.name]
    t = time.time()
    df = df_utils.load_df(path)
    callback({'name': 'load_finished', 'time': time.time() - t})
    t = time.time()
    processed_df = preprocess_l2_inc_df(df, date_str)
    callback({'name': 'preproc_finished', 'time': time.time() - t})

    def split_callback(i, t):
        callback({'name': 'split_finished', 'time': t})

    gen = gen_split_l2_inc_df_and_pad_with_snapshot(processed_df, chunk_size_kb, split_callback)
    catalog_items = []
    split_id = 0
    num_splits = 0

    STORE_PARALLELISM = 10
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=STORE_PARALLELISM)
    store_futures = []

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
            executor.submit(functools.partial(store_df, df=split, path=catalog_item.path, callback=callback))
        )

        catalog_items.append(catalog_item)
        split_id += 1
        num_splits += 1

    for catalog_item in catalog_items:
        catalog_item.extras['num_splits'] = num_splits

    concurrent.futures.wait(store_futures)
    t = time.time()
    res = ray.get(db_actor.write_batch.remote(catalog_items))
    callback({'name': 'write_finished', 'time': time.time() - t})
    return res


def store_df(df: pd.DataFrame, path: str, callback: Callable):
    t = time.time()
    df_utils.store_df(path, df)
    callback({'name': 'store_finished', 'time': time.time() - t})

@ray.remote(num_cpus=0.9, resources={'worker_size_large': 1, 'instance_spot': 1})
def mock_split(callback, wait=1):
    t = time.time()
    time.sleep(1)
    callback({'name': 'load_finished', 'time': time.time() - t})
    t = time.time()
    time.sleep(1)
    callback({'name': 'preproc_finished', 'time': time.time() - t})
    for _ in range(10):
        t = time.time()
        time.sleep(wait)
        callback({'name': 'split_finished', 'time': time.time() - t})
        time.sleep(0.5)
        callback({'name': 'store_finished', 'time': time.time() - t})
    t = time.time()
    time.sleep(1)
    callback({'name': 'write_finished', 'time': time.time() - t})
    return {}


def make_catalog_item(df: pd.DataFrame, input_item: InputItem) -> DataCatalog:
    source = input_item[DataCatalog.source.name]
    if source not in ['cryptofeed', 'cryptotick']:
        raise ValueError(f'Unknown source: {source}')

    catalog_item_params = input_item.copy()
    _time_range = df_utils.time_range(df)

    date_str = datetime.fromtimestamp(_time_range[1], tz=pytz.utc).strftime('%Y-%m-%d')
    # check if end_ts is also same date:
    date_str_end = datetime.fromtimestamp(_time_range[2], tz=pytz.utc).strftime('%Y-%m-%d')
    if date_str != date_str_end:
        raise ValueError(f'start_ts and end_ts belong to different dates: {date_str}, {date_str_end}')

    catalog_item_params.update({
        DataCatalog.start_ts.name: _time_range[1],
        DataCatalog.end_ts.name: _time_range[2],
        DataCatalog.size_in_memory_kb.name: df_utils.get_size_kb(df),
        DataCatalog.num_rows.name: df_utils.get_num_rows(df),
        DataCatalog.date.name: date_str,
    })

    # TODO l2_book -> l2_inc
    if catalog_item_params[DataCatalog.data_type.name] == 'l2_book':
        if source == 'cryptofeed':
            snapshot_ts = cryptofeed_l2_utils.get_snapshot_ts(df)
        else:
            snapshot_ts = cryptotick_l2_utils.get_snapshot_ts(df)
        if snapshot_ts is not None:
            meta = {
                'snapshot_ts': snapshot_ts
            }
            catalog_item_params[DataCatalog.meta.name] = meta

    df_hash = df_utils.hash_df(df)
    catalog_item_params[DataCatalog.hash.name] = df_hash

    res = DataCatalog(**catalog_item_params)
    if res.path is None:
        if source != 'cryptotick':
            raise ValueError(f'Empty path only allowed for cryptotick')
        res.path = _construct_s3_path(res)

    return res
