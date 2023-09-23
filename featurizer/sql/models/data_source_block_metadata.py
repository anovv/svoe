from sqlalchemy import Column, String, JSON, DateTime, func, Integer

from common.db.base import Base

DEFAULT_COMPACTION = 'raw'


class DataSourceBlockMetadata(Base):
    __tablename__ = 'data_source_blocks_metadata'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    key = Column(String(32), primary_key=True)
    data_source_definition = Column(String(32), primary_key=True)
    start_ts = Column(String(32), primary_key=True)
    end_ts = Column(String(32), primary_key=True)

    day = Column(String(32), primary_key=True)

    path = Column(String(512), unique=True)

    # TODO hash is unique only for given owner_id
    hash = Column(String(512), unique=True)

    num_rows = Column(Integer)
    size_kb = Column(String(32))
    size_in_memory_kb = Column(String(32))
    meta = Column(JSON)
    extras = Column(JSON)

    compaction = Column(String(32), primary_key=True, default=DEFAULT_COMPACTION)

    def __init__(self, **kwargs):
        # set default values for model instance
        super().__init__(**kwargs)
        if self.compaction is None:
            setattr(self, DataSourceBlockMetadata.compaction.name, DEFAULT_COMPACTION)


def build_data_source_block_path(item: DataSourceBlockMetadata, prefix: str) -> str:
    res = prefix
    for field in [
        DataSourceBlockMetadata.owner_id.name,
        DataSourceBlockMetadata.data_source_definition.name,
        DataSourceBlockMetadata.key.name,
        DataSourceBlockMetadata.compaction.name,
        DataSourceBlockMetadata.version.name,
        DataSourceBlockMetadata.day.name, # date should be last so we can identify all data by prefix in s3
    ]:
        v = item.__dict__[field]
        if v is not None and len(v) > 0:
            res += f'{v}/'
    res += f'{int(item.__dict__[DataSourceBlockMetadata.start_ts.name])}-{item.__dict__[DataSourceBlockMetadata.hash.name]}.parquet.gz'
    return res
