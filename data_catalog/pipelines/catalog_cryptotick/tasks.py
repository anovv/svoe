from typing import List, Tuple

import pandas as pd
import ray

from data_catalog.common.data_models.models import InputItem
from data_catalog.common.utils.sql.models import DataCatalog, make_catalog_item
from featurizer.features.data.l2_book_incremental.cryptotick.utils import preprocess_l2_inc_df, \
    split_l2_inc_df_and_pad_with_snapshot
from utils.pandas import df_utils


@ray.remote
def load_split_catalog_l2_inc_df(input_item: InputItem, chunk_size_kb: int, date_str: str) -> Tuple[List[pd.DataFrame], List[DataCatalog]]:
    print('Load started')
    path = input_item[DataCatalog.path.name]
    if '.csv' in path:
        extension = 'csv'
    elif '.parquet' in path:
        extension = 'parquet'
    else:
        raise ValueError(f'Unknown file extension: {path}')

    df = df_utils.load_df(path, extension=extension)
    print('Load finished')
    print('Preproc started')
    processed_df = preprocess_l2_inc_df(df, date_str)
    print('Preproc finished')
    print('Split started')
    splits = split_l2_inc_df_and_pad_with_snapshot(processed_df, chunk_size_kb)
    print('Split finished')
    print('Cataloguing started')
    catalog_items = []
    split_id = 0
    for split in splits:
        item_split = input_item.copy()

        # additional info to be passed to catalog item
        compaction = f'{chunk_size_kb}kb' if chunk_size_kb < 1024 else f'{round(chunk_size_kb / 1024, 2)}mb'
        item_split[DataCatalog.compaction.name] = compaction
        item_split[DataCatalog.source.name] = 'cryptotick'
        item_split[DataCatalog.extras.name] = {
            'source_path': item_split[DataCatalog.path.name],
            'split_id': split_id,
            'num_splits': len(splits),
        }

        # remove raw source path so it is constructed by SqlAlchemy default value when making catalog item
        del item_split[DataCatalog.path.name]

        catalog_items.append(make_catalog_item(split, item_split))

    print('Cataloguing finished')
    return splits, catalog_items
