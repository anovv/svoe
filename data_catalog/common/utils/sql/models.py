import json

from sqlalchemy import Column, String, JSON, DateTime, func, Integer
from sqlalchemy.orm import declarative_base
from data_catalog.common.data_models.models import InputItem, IndexItem

Base = declarative_base()

# defaults
DEFAULT_SOURCE = 'cryptofeed'
DEFAULT_VERSION = ''
DEFAULT_COMPACTION = 'raw'
DEFAULT_EXTRAS = ''
DEFAULT_INSTRUMENT_EXTRA = ''

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
    base = Column(String(32))
    quote = Column(String(32))

    num_rows = Column(Integer)
    size_kb = Column(String(32))
    size_in_memory_kb = Column(String(32))
    meta = Column(JSON)

    # TODO these should be in a separate index table
    # defaultable
    instrument_extra = Column(String(32), primary_key=True, default=DEFAULT_INSTRUMENT_EXTRA)
    source = Column(String(32), primary_key=True, default=DEFAULT_SOURCE)
    compaction = Column(String(32), primary_key=True, default=DEFAULT_COMPACTION)
    version = Column(String(256), primary_key=True, default=DEFAULT_VERSION)
    extras = Column(JSON, default=DEFAULT_EXTRAS)

# TODO add bucket name
def construct_s3_path(item: IndexItem, bucket: str = '') -> str:
    res = f's3://{bucket}/'
    for field in [
        DataCatalog.data_type,
        DataCatalog.exchange,
        DataCatalog.instrument_type,
        DataCatalog.instrument_extra,
        DataCatalog.symbol,
        DataCatalog.date,

        # TODO defaultables are not present in index_item
        DataCatalog.source,
        DataCatalog.compaction,
        DataCatalog.version,
        DataCatalog.extras
    ]:
        res += f'{item[field]}/'
    uuid = None # TODO
    res += f'{uuid}.parquet.gz'
    return res
