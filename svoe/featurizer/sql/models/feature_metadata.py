from sqlalchemy import Column, String, JSON, DateTime, func

from svoe.common.db.base import Base

DEFAULT_VERSION = ''


class FeatureMetadata(Base):
    __tablename__ = 'features_metadata'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    key = Column(String(32), primary_key=True)
    feature_definition = Column(String(32), primary_key=True)

    # TODO owner_id + feature_name should be unique
    feature_name = Column(String(32), unique=True, nullable=True)

    params = Column(JSON)
    extras = Column(JSON)
    version = Column(String(256), primary_key=True, default=DEFAULT_VERSION)

    def __init__(self, **kwargs):
        # set default values for model instance
        super().__init__(**kwargs)
        if self.version is None:
            setattr(self, FeatureMetadata.version.name, DEFAULT_VERSION)
