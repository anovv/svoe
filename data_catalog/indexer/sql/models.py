from sqlalchemy import Column, String, JSON, DateTime, func, Float, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class DataCatalog(Base):
    __tablename__ = 'data_catalog'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # TODO add id cols? hash?

    # composite primary key cols
    data_type = Column(String(40), primary_key=True)
    args = Column(JSON, primary_key=True)
    exchange = Column(String(40), primary_key=True)
    instrument_type = Column(String(40), primary_key=True)
    instrument_extra = Column(JSON, primary_key=True)
    symbol = Column(JSON, primary_key=True)
    base = Column(JSON, primary_key=True)
    quote = Column(JSON, primary_key=True)
    start_ts = Column(Float, primary_key=True)
    end_ts = Column(Float, primary_key=True)
    source = Column(String(40), primary_key=True)
    compaction = Column(String(40), primary_key=True)
    version = Column(String(40), primary_key=True, unique=True)

    path = Column(String(40), unique=True)
    size_kb = Column(Float)
    size_in_memory_kb = Column(Float)
    num_rows = Column(Integer)
    meta = Column(JSON)
    extras = Column(JSON)

    # TODO owner_id?
