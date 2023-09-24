from sqlalchemy import Column, String, JSON, DateTime, func, Integer

from common.db.base import Base

DEFAULT_COMPACTION = 'raw'


class FeatureBlockMetadata(Base):
    __tablename__ = 'feature_blocks_metadata'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    key = Column(String(32), primary_key=True)
    feature_definition = Column(String(32), primary_key=True)
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
            setattr(self, FeatureBlockMetadata.compaction.name, DEFAULT_COMPACTION)


def build_feature_block_path(item: FeatureBlockMetadata, prefix: str) -> str:
    res = prefix
    for field in [
        FeatureBlockMetadata.owner_id.name,
        FeatureBlockMetadata.feature_definition.name,
        FeatureBlockMetadata.key.name,
        FeatureBlockMetadata.compaction.name,
        FeatureBlockMetadata.day.name, # date should be last so we can identify all data by prefix in s3
    ]:
        v = item.__dict__[field]
        if v is not None and len(v) > 0:
            res += f'{v}/'
    res += f'{int(item.__dict__[FeatureBlockMetadata.start_ts.name])}-{item.__dict__[FeatureBlockMetadata.hash.name]}.parquet.gz'
    return res
