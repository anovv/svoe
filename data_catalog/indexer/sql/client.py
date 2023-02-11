from typing import Optional, Dict, List

from sqlalchemy import create_engine, Column, String, JSON, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from data_catalog.indexer.sql.models import DataCatalog, add_defaults
from data_catalog.indexer.indexer import IndexItemBatch, InputItemBatch

import os

Base = declarative_base()
Session = sessionmaker()


class MysqlClient:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config
        if self.config is None:
            self.config = {}
        self.engine = self._init_engine()

    def _init_engine(self):
        user = self.config.get('mysql_user', os.getenv('MYSQL_USER'))
        password = self.config.get('mysql_password', os.getenv('MYSQL_PASSWORD'))
        host = self.config.get('mysql_host', os.getenv('MYSQL_HOST'))
        port = self.config.get('mysql_port', os.getenv('MYSQL_PORT'))
        db = self.config.get('mysql_database', os.getenv('MYSQL_DATABASE'))
        url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'
        engine = create_engine(url, echo=True)
        Session.configure(bind=engine)
        return engine

    def create_tables(self):
        # creates if not exists
        Base.metadata.create_all(self.engine)

    def write_index_items_batch(self, batch: IndexItemBatch):
        # TODO figure out insert_or_update logic
        # use dict unpacking
        # https://stackoverflow.com/questions/31750441/generalised-insert-into-sqlalchemy-using-dictionary
        objects = []
        for index_item in batch:
            index_item = add_defaults(index_item)
            # TODO handle failed unpacking (e.g. missing keys)
            objects.append(DataCatalog(**index_item))
        session = Session()
        session.bulk_save_objects(objects)
        session.commit()
        return # TODO return result?

    def check_exists(self, batch: InputItemBatch) -> InputItemBatch:
        return []

