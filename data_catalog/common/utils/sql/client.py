from typing import Optional, Dict, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data_catalog.common.utils.sql.models import DataCatalog, Base, DEFAULT_COMPACTION, DEFAULT_SOURCE, \
    DEFAULT_VERSION, DEFAULT_INSTRUMENT_EXTRA
from data_catalog.common.data_models.models import InputItemBatch

import os

Session = sessionmaker()


DEFAULT_CONFIG = {
    'mysql_user': 'root',
    'mysql_password': '',
    'mysql_host': '127.0.0.1',
    'mysql_port': '3306',
    'mysql_database': 'svoe_db',
}


class MysqlClient:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config
        if self.config is None:
            self.config = DEFAULT_CONFIG
        self.engine = self._init_engine()

    def _init_engine(self):
        user = self.config.get('mysql_user', os.getenv('MYSQL_USER'))
        password = self.config.get('mysql_password', os.getenv('MYSQL_PASSWORD'))
        host = self.config.get('mysql_host', os.getenv('MYSQL_HOST'))
        port = self.config.get('mysql_port', os.getenv('MYSQL_PORT'))
        db = self.config.get('mysql_database', os.getenv('MYSQL_DATABASE'))
        url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'
        engine = create_engine(url, echo=False)
        Session.configure(bind=engine)
        return engine

    def create_tables(self):
        # creates if not exists
        Base.metadata.create_all(self.engine)

    # TODO separate api methods and pipeline methods

    # see 2nd comment in https://stackoverflow.com/questions/3659142/bulk-insert-with-sqlalchemy-orm
    # RE: bulk insert perf
    def write_index_item_batch(self, batch: List[DataCatalog]):
        print(batch)
        # TODO figure out insert_or_update logic
        # use dict unpacking
        # https://stackoverflow.com/questions/31750441/generalised-insert-into-sqlalchemy-using-dictionary
        # objects = []
        # for index_item in batch:
        #     # TODO handle failed unpacking (e.g. missing keys)
        #     # objects.append(DataCatalog(**index_item))
        session = Session()
        session.bulk_save_objects(batch)

        # TODO try catch and handle
        # 1) connection issues
        # 2) duplicate entries
        session.commit()
        print(f'Written {len(batch)} index items to Db')
        return # TODO return result?

    def filter_batch(self, batch: InputItemBatch) -> InputItemBatch:
        # use path as a unique id per block
        items = batch[1]
        meta = batch[0]
        paths = [item['path'] for item in items]
        query_in = DataCatalog.path.in_(paths)
        session = Session()
        select_in_db = session.query(DataCatalog.path).filter(query_in)
        res = [r[0] for r in select_in_db.all()]
        non_exist = list(filter(lambda item: item['path'] not in res, items))
        print(f'Checked db for items: {len(non_exist)} not in DB')
        return meta, non_exist

    # api methods
    # TODO typing
    def select(
        self,
        exchange: str,
        data_type: str,
        instrument_type: str,
        symbol: str,
        instrument_extra: str = DEFAULT_INSTRUMENT_EXTRA,
        compaction: str = DEFAULT_COMPACTION,
        source: str = DEFAULT_SOURCE,
        version: str = DEFAULT_VERSION,
        extras: str = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List:
        # TODO instrument_extra
        session = Session()
        res = session.query(DataCatalog).filter_by(
            exchange=exchange,
            data_type=data_type,
            instrument_type=instrument_type,
            symbol=symbol,
            instrument_extra=instrument_extra,
            compaction=compaction,
            source=source,
            version=version,
            extras=extras
        ).order_by(DataCatalog.start_ts).all()
        # TODO this adds unnecessary sqlalchemy fields, remove to reduce memory footprint
        return [r.__dict__ for r in res]

