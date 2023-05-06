from sqlalchemy import Column, String, JSON, DateTime, func, Integer
from sqlalchemy.orm import declarative_base

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
