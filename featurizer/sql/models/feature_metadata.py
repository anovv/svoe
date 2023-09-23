from sqlalchemy import Column, String, JSON, DateTime, func, Integer

from common.db.base import Base

DEFAULT_VERSION = ''


class FeatureMetadata(Base):
    __tablename__ = 'features_metadata'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    feature_name = Column(String(32), primary_key=True)
    key = Column(String(32), primary_key=True)
    feature_definition = Column(String(32), primary_key=True)
    params = Column(JSON)
    extras = Column(JSON)
    version = Column(String(256), primary_key=True, default=DEFAULT_VERSION)
