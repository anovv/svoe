import uuid
from datetime import datetime

import pandas as pd
import pytz
from sqlalchemy import Column, String, JSON, DateTime, func, Integer
from sqlalchemy.orm import declarative_base
from data_catalog.common.data_models.models import InputItem
import featurizer.features.data.l2_book_incremental.cryptofeed.utils as cryptofeed_l2_utils
import featurizer.features.data.l2_book_incremental.cryptotick.utils as cryptotick_l2_utils
from utils.pandas import df_utils

Base = declarative_base()

# defaults
DEFAULT_SOURCE = 'cryptofeed'
DEFAULT_VERSION = ''
DEFAULT_COMPACTION = 'raw'
DEFAULT_INSTRUMENT_EXTRA = ''

SVOE_S3_CATALOGED_DATA_BUCKET = 'svoe-cataloged-data'


# TODO figure out float precision issues
class DataCatalog(Base):
    __tablename__ = 'data_catalog'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # TODO add id cols?
    # TODO add owner_id?

    # composite primary key cols
    data_type = Column(String(32), primary_key=True)
    exchange = Column(String(32), primary_key=True)
    instrument_type = Column(String(32), primary_key=True)

    symbol = Column(String(32), primary_key=True)

    start_ts = Column(String(32), primary_key=True)
    end_ts = Column(String(32), primary_key=True)
    date = Column(String(32), primary_key=True)

    # TODO this should be a secondary key
    path = Column(String(512), unique=True)
    hash = Column(String(512), unique=True)
    base = Column(String(32))
    quote = Column(String(32))

    num_rows = Column(Integer)
    size_kb = Column(String(32))
    size_in_memory_kb = Column(String(32))
    meta = Column(JSON)
    extras = Column(JSON)

    # TODO these should be in a separate index table
    # defaultable
    instrument_extra = Column(String(32), primary_key=True, default=DEFAULT_INSTRUMENT_EXTRA)
    source = Column(String(32), primary_key=True, default=DEFAULT_SOURCE)
    compaction = Column(String(32), primary_key=True, default=DEFAULT_COMPACTION)
    version = Column(String(256), primary_key=True, default=DEFAULT_VERSION)

    def __init__(self, **kwargs):
        # set default values for model instance
        super().__init__(**kwargs)
        if self.instrument_extra is None:
            setattr(self, DataCatalog.instrument_extra.name, DEFAULT_INSTRUMENT_EXTRA)
        if self.source is None:
            setattr(self, DataCatalog.source.name, DEFAULT_SOURCE)
        if self.compaction is None:
            setattr(self, DataCatalog.compaction.name, DEFAULT_COMPACTION)
        if self.version is None:
            setattr(self, DataCatalog.version.name, DEFAULT_VERSION)


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


def _construct_s3_path(item: DataCatalog) -> str:
    res = f's3://{SVOE_S3_CATALOGED_DATA_BUCKET}/'
    for field in [
        DataCatalog.data_type.name,
        DataCatalog.exchange.name,
        DataCatalog.instrument_type.name,
        DataCatalog.instrument_extra.name,
        DataCatalog.symbol.name,
        DataCatalog.source.name,
        DataCatalog.compaction.name,
        DataCatalog.version.name,
        DataCatalog.date.name, # date should be last so we can identify all data by prefix in s3
    ]:
        v = item.__dict__[field]
        if v is not None and len(v) > 0:
            res += f'{v}/'
    res += f'{int(item.__dict__[DataCatalog.start_ts.name])}-{item.__dict__[DataCatalog.hash.name]}.parquet.gz'
    return res
