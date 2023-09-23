import concurrent
import functools
import time
from datetime import datetime
from typing import Dict, Callable, Optional

import pandas as pd
import pytz
import ray

from featurizer.data_definitions.common.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.data_definitions.common.trades.cryptotick.utils import preprocess_trades_df
from featurizer.data_definitions.common.trades.trades import TradesData
from featurizer.sql.db_actor import DbActor
from featurizer.data_catalog.common.data_models.models import InputItem
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.data_definitions.common.l2_book_incremental.cryptotick.utils import preprocess_l2_inc_df, \
    gen_split_l2_inc_df_and_pad_with_snapshot, get_snapshot_ts
from common.pandas import df_utils
from common.pandas.df_utils import gen_split_df_by_mem
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter


# TODO set cpu separately when running on aws kuber cluster
@ray.remote(num_cpus=2, resources={'worker_size_large': 1, 'instance_spot': 1})
def load_split_catalog_store_df(
    input_item: InputItem,
    chunk_size_kb: int,
    date_str: str, # TODO date -> day
    db_actor: DbActor,
    data_store_adapter: DataStoreAdapter,
    callback: Optional[Callable] = None
) -> Dict:
    path = input_item[DataSourceBlockMetadata.path.name]
    data_source_definition = input_item[DataSourceBlockMetadata.data_source_definition.name]
    t = time.time()
    df = data_store_adapter.load_df(path)
    callback({'name': 'load_finished', 'time': time.time() - t})
    t = time.time()

    def split_callback(i, t):
        callback({'name': 'split_finished', 'time': t})

    if data_source_definition == CryptotickL2BookIncrementalData.__name__:
        processed_df = preprocess_l2_inc_df(df, date_str)
        gen = gen_split_l2_inc_df_and_pad_with_snapshot(processed_df, chunk_size_kb, split_callback)
    elif data_source_definition == TradesData.__name__:
        processed_df = preprocess_trades_df(df)
        gen = gen_split_df_by_mem(processed_df, chunk_size_kb, split_callback)
    # elif data_type == 'quotes':
    #     processed_df = preprocess_l2_inc_df(df, date_str)
    else:
        raise ValueError(f'Unknown data_source_definition: {data_source_definition}')

    callback({'name': 'preproc_finished', 'time': time.time() - t})
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
        item_split[DataSourceBlockMetadata.compaction.name] = compaction
        item_split[DataSourceBlockMetadata.extras.name] = {
            'source_path': item_split[DataSourceBlockMetadata.path.name],
            'split_id': split_id,
        }

        # remove raw source path so it is constructed by SqlAlchemy default value when making catalog item
        del item_split[DataSourceBlockMetadata.path.name]

        catalog_item = make_data_source_block_metadata(split, item_split, data_store_adapter)
        store_futures.append(
            executor.submit(functools.partial(store_df, df=split, path=catalog_item.path, data_store_adapter=data_store_adapter, callback=callback))
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


def store_df(df: pd.DataFrame, path: str, data_store_adapter: DataStoreAdapter, callback: Callable):
    t = time.time()
    data_store_adapter.store_df(path, df)
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


def make_data_source_block_metadata(df: pd.DataFrame, input_item: InputItem, data_store_adapter: DataStoreAdapter) -> DataSourceBlockMetadata:
    source = input_item[DataSourceBlockMetadata.source.name]
    if source not in ['cryptofeed', 'cryptotick']:
        raise ValueError(f'Unknown source: {source}')

    block_metadata_params = input_item.copy()
    _time_range = df_utils.time_range(df)

    date_str = datetime.fromtimestamp(_time_range[1], tz=pytz.utc).strftime('%Y-%m-%d')
    # check if end_ts is also same date:
    date_str_end = datetime.fromtimestamp(_time_range[2], tz=pytz.utc).strftime('%Y-%m-%d')
    if date_str != date_str_end:
        raise ValueError(f'start_ts and end_ts belong to different dates: {date_str}, {date_str_end}')

    block_metadata_params.update({
        DataSourceBlockMetadata.owner_id.name: '0', # default owner
        DataSourceBlockMetadata.start_ts.name: _time_range[1],
        DataSourceBlockMetadata.end_ts.name: _time_range[2],
        DataSourceBlockMetadata.size_in_memory_kb.name: df_utils.get_size_kb(df),
        DataSourceBlockMetadata.num_rows.name: df_utils.get_num_rows(df),
        DataSourceBlockMetadata.day.name: date_str,
    })

    # TODO l2_book -> l2_inc
    if block_metadata_params[DataSourceBlockMetadata.data_source_definition.name] == CryptotickL2BookIncrementalData.__name__:
        snapshot_ts = get_snapshot_ts(df)
        if snapshot_ts is not None:
            meta = {
                'snapshot_ts': snapshot_ts
            }
            block_metadata_params[DataSourceBlockMetadata.meta.name] = meta

    df_hash = df_utils.hash_df(df)
    block_metadata_params[DataSourceBlockMetadata.hash.name] = df_hash

    res = DataSourceBlockMetadata(**block_metadata_params)
    if res.path is None:
        res.path = data_store_adapter.make_data_source_block_path(res)

    return res
