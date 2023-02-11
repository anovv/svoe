from sqlalchemy import Column, String, JSON, DateTime, func, Float, Integer
from sqlalchemy.orm import declarative_base
from data_catalog.indexer.models import InputItem

Base = declarative_base()


class DataCatalog(Base):
    __tablename__ = 'data_catalog'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # TODO add id cols?

    # composite primary key cols
    data_type = Column(String(32), primary_key=True)
    args = Column(JSON, primary_key=True)
    exchange = Column(String(32), primary_key=True)
    instrument_type = Column(String(32), primary_key=True)
    instrument_extra = Column(JSON, primary_key=True)
    symbol = Column(JSON, primary_key=True)
    base = Column(JSON, primary_key=True)
    quote = Column(JSON, primary_key=True)
    start_ts = Column(Float, primary_key=True)
    end_ts = Column(Float, primary_key=True)
    source = Column(String(32), primary_key=True)
    compaction = Column(String(32), primary_key=True)
    version = Column(String(512), primary_key=True, unique=True)

    path = Column(String(512), unique=True)
    size_kb = Column(Float)
    size_in_memory_kb = Column(Float)
    num_rows = Column(Integer)
    meta = Column(JSON)
    extras = Column(JSON)

    # TODO owner_id?


def add_defaults(item: InputItem) -> InputItem:
    # TODO add missing keys
    return item
