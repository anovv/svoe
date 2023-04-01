import json
from datetime import datetime

import pandas as pd
import pytz

import featurizer.features.data.l2_book_incremental.cryptofeed.utils as cryptofeed_l2_utils
import featurizer.features.data.l2_book_incremental.cryptotick.utils as cryptotick_l2_utils

from data_catalog.common.data_models.models import InputItem, IndexItem
from data_catalog.common.utils.sql.models import DataCatalog, construct_s3_path
from utils.pandas import df_utils


def make_index_item(df: pd.DataFrame, input_item: InputItem, source: str) -> IndexItem:
    if source not in ['cryptofeed', 'cryptotick']:
        raise ValueError(f'Unknown source: {source}')

    index_item = input_item.copy()
    _time_range = df_utils.time_range(df)

    date_str = datetime.fromtimestamp(_time_range[1], tz=pytz.utc).strftime('%Y-%m-%d')
    # check if end_ts is also same date:
    date_str_end = datetime.fromtimestamp(_time_range[2], tz=pytz.utc).strftime('%Y-%m-%d')
    if date_str != date_str_end:
        raise ValueError(f'start_ts and end_ts belong to different dates: {date_str}, {date_str_end}')

    index_item.update({
        DataCatalog.start_ts.name: _time_range[1],
        DataCatalog.end_ts.name: _time_range[2],
        DataCatalog.size_in_memory_kb.name: df_utils.get_size_kb(df),
        DataCatalog.num_rows.name: df_utils.get_num_rows(df),
        DataCatalog.date.name: date_str
    })

    # TODO l2_book -> l2_inc
    if index_item['data_type'] == 'l2_book':
        if source == 'cryptofeed':
            snapshot_ts = cryptofeed_l2_utils.get_snapshot_ts(df)
        else:
            snapshot_ts = cryptotick_l2_utils.get_snapshot_ts(df)
        if snapshot_ts is not None:
            meta = {
                'snapshot_ts': snapshot_ts
            }
            index_item['meta'] = json.dumps(meta)

    if DataCatalog.path.name not in index_item:
        index_item['path'] = construct_s3_path(index_item)

    return index_item
