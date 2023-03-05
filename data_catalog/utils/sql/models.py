import json

from sqlalchemy import Column, String, JSON, DateTime, func, Integer, Float
from sqlalchemy.orm import declarative_base
from data_catalog.indexer.models import InputItem

Base = declarative_base()

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

    # TODO this should be JSON but MySQL does not allow JSON keys
    instrument_extra = Column(String(32), primary_key=True)
    symbol = Column(String(32), primary_key=True)

    # TODO do base/quote need to be part of key? they are derived from symbol
    base = Column(String(32), primary_key=True)
    quote = Column(String(32), primary_key=True)
    # start_ts = Column(Float(precision='16,6'), primary_key=True)
    start_ts = Column(String(32), primary_key=True)
    # end_ts = Column(Float(precision='16,6'), primary_key=True)
    end_ts = Column(String(32), primary_key=True)

    # TODO this should be a secondary key
    path = Column(String(512), unique=True)

    num_rows = Column(Integer)
    # size_kb = Column(Float(precision='16,6'))
    size_kb = Column(String(32))
    # size_in_memory_kb = Column(Float(precision='16,6'))
    size_in_memory_kb = Column(String(32))
    meta = Column(JSON)

    # defaultable
    source = Column(String(32), primary_key=True)
    compaction = Column(String(32), primary_key=True)
    version = Column(String(256), primary_key=True)
    extras = Column(JSON)


# TODO sync keys with DataCatalog sql model
def add_defaults(item: InputItem) -> InputItem:
    item.update({
        'source': 'cryptofeed',
        'compaction': 'raw',
        'version': '',
        'extras': json.dumps({}),
    })

    return item
