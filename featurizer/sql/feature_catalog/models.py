from sqlalchemy import Column, String, JSON, DateTime, func, Integer

from common.db.base import Base

# from sqlalchemy.orm import declarative_base


# defaults
DEFAULT_VERSION = ''
DEFAULT_COMPACTION = 'raw'

SVOE_S3_FEATURE_CATALOG_BUCKET = 'svoe-feature-catalog-data'


class FeatureCatalog(Base):
    __tablename__ = 'feature_catalog'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # TODO serialize dependency tree?

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    feature_def = Column(String(32), primary_key=True)
    feature_key = Column(String(256), primary_key=True)

    start_ts = Column(String(32), primary_key=True)
    end_ts = Column(String(32), primary_key=True)

    # TODO rename date -> day
    date = Column(String(32), primary_key=True)

    sampling = Column(String(32))
    window = Column(String(32))

    # TODO this should be a secondary key
    path = Column(String(512), unique=True)
    hash = Column(String(512), unique=True)

    data_params = Column(JSON)
    feature_params = Column(JSON)
    num_rows = Column(Integer)
    size_kb = Column(String(32))
    size_in_memory_kb = Column(String(32))
    meta = Column(JSON)
    extras = Column(JSON)
    tags = Column(JSON)

    # TODO these should be in a separate index table
    # defaultable
    compaction = Column(String(32), primary_key=True, default=DEFAULT_COMPACTION)
    version = Column(String(256), primary_key=True, default=DEFAULT_VERSION)

    def __init__(self, **kwargs):
        # set default values for model instance
        super().__init__(**kwargs)
        if self.compaction is None:
            setattr(self, FeatureCatalog.compaction.name, DEFAULT_COMPACTION)
        if self.version is None:
            setattr(self, FeatureCatalog.version.name, DEFAULT_VERSION)


def _construct_feature_catalog_s3_path(item: FeatureCatalog) -> str:
    res = f's3://{SVOE_S3_FEATURE_CATALOG_BUCKET}/'
    for field in [
        FeatureCatalog.feature_def.name,
        FeatureCatalog.feature_key.name,
        FeatureCatalog.version.name,
        FeatureCatalog.compaction.name,
        FeatureCatalog.date.name, # date should be last so we can identify all data by prefix in s3
    ]:
        v = item.__dict__[field]
        if v is not None and len(v) > 0:
            res += f'{v}/'
    res += f'{int(item.__dict__[FeatureCatalog.start_ts.name])}-{item.__dict__[FeatureCatalog.hash.name]}.parquet.gz'
    return res
