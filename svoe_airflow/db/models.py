from sqlalchemy import Column, String, Text, DateTime, func
from common.db.base import Base


class DagConfigEncoded(Base):
    __tablename__ = 'dag_configs'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # composite primary key cols
    owner_id = Column(String(32), primary_key=True)
    dag_name = Column(String(32), primary_key=True)

    dag_config_encoded = Column(Text())
    compilation_error = Column(Text())
