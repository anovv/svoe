from sqlalchemy import Column, String, JSON, DateTime, func

from common.db.base import Base

SVOE_S3_FEATURE_DEFINITIONS_BUCKET = 'svoe-feature-definitions'

# TODO sync this with FeatureDefinition class somehow?
class FeatureDefinitionDB(Base):
    __tablename__ = 'feature_definitions'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    feature_group = Column(String(32), primary_key=True)
    feature_definition = Column(String(32), primary_key=True)
    version = Column(String(256), primary_key=True)

    path = Column(String(512), unique=True)

    # TODO is it needed?
    hash = Column(String(512), unique=True)

    extras = Column(JSON)
    tags = Column(JSON)


def construct_feature_def_s3_path(item: FeatureDefinitionDB) -> str:
    res = f's3://{SVOE_S3_FEATURE_DEFINITIONS_BUCKET}/'
    for field in [
        FeatureDefinitionDB.owner_id.name,
        FeatureDefinitionDB.feature_group.name,
        FeatureDefinitionDB.feature_definition.name,
        FeatureDefinitionDB.version.name
    ]:
        v = item.__dict__[field]
        res += f'{v}/'

    return res