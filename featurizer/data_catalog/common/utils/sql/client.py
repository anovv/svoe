from typing import Optional, Dict, List, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from featurizer.data_catalog.common.utils.sql.models import DataCatalog, Base
from featurizer.data_catalog.common.data_models.models import InputItemBatch

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
        user = os.getenv('MYSQL_USER', self.config.get('mysql_user'))
        password = os.getenv('MYSQL_PASSWORD', self.config.get('mysql_password'))
        host = os.getenv('MYSQL_HOST', self.config.get('mysql_host'))
        port = os.getenv('MYSQL_PORT', self.config.get('mysql_port'))
        db = os.getenv('MYSQL_DATABASE', self.config.get('mysql_database'))
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
    def write_catalog_item_batch(self, batch: List[DataCatalog]):
        # TODO figure out insert_or_update logic
        session = Session()
        session.bulk_save_objects(batch)

        # TODO try catch and handle
        # 1) connection issues
        # 2) duplicate entries
        session.commit()
        print(f'Written {len(batch)} index items to Db')
        return # TODO return result?


    def filter_cryptofeed_batch(self, batch: InputItemBatch) -> InputItemBatch:
        # use path as a unique id per block
        items = batch[1]
        meta = batch[0]
        paths = [item[DataCatalog.path.name] for item in items]
        query_in = DataCatalog.path.in_(paths)
        session = Session()
        select_in_db = session.query(DataCatalog.path).filter(query_in)
        res = [r[0] for r in select_in_db.all()]
        non_exist = list(filter(lambda item: item[DataCatalog.path.name] not in res, items))
        print(f'Checked db for items: {len(non_exist)} not in DB')
        return meta, non_exist


    def filter_cryptotick_batch(self, batch: InputItemBatch) -> InputItemBatch:
        items = batch[1]
        meta = batch[0]
        paths = [item[DataCatalog.path.name] for item in items]
        session = Session()
        query_in = DataCatalog.extras['source_path'].in_(paths)
        select_in_db = session.query(DataCatalog).filter(query_in)
        rows = select_in_db.all()
        if len(rows) == 0:
            return batch
        non_exist = []
        for item in items:
            # check if for given item num_splits == num returned rows
            rows_for_item = list(filter(lambda row: row.extras['source_path'] == item[DataCatalog.path.name], rows))
            if len(rows_for_item) == 0:
                non_exist.append(item)
                continue
            # TODO verify split ids?
            num_splits = rows_for_item[0].extras['num_splits']
            if len(rows_for_item) != num_splits:
                non_exist.append(item)

        print(f'Checked db for items: {len(non_exist)} not in DB')
        return meta, non_exist

    # api methods
    def select(
        self,
        exchanges: List[str],
        data_types: List[str],
        instrument_types: List[str],
        symbols: List[str],
        instrument_extra: Optional[str] = None,
        compaction: Optional[str] = None,
        source: Optional[str] = None,
        version: Optional[str] = None,
        extras: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Any]:
        # TODO instrument_extra
        args = {
            DataCatalog.exchange.name: exchanges,
            DataCatalog.data_type.name: data_types,
            DataCatalog.instrument_type.name: instrument_types,
            DataCatalog.symbol.name: symbols
        }
        if compaction is not None:
            args[DataCatalog.compaction.name] = compaction
        if source is not None:
            args[DataCatalog.symbol.name] = source
        if version is not None:
            args[DataCatalog.version.name] = version
        if extras is not None:
            args[DataCatalog.extras.name] = extras

        session = Session()
        f = session.query(DataCatalog).filter_by(**args)
        if start_date is not None:
            f = f.filter(DataCatalog.date >= start_date)
        if end_date is not None:
            f = f.filter(DataCatalog.date <= end_date)
        res = f.order_by(DataCatalog.start_ts).all()

        # TODO this adds unnecessary sqlalchemy fields, remove to reduce memory footprint
        return [r.__dict__ for r in res]

