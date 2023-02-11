from typing import Optional, Dict, List

from sqlalchemy import create_engine, Column, String, JSON, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from data_catalog.indexer.sql.models import DataCatalog

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

    def write_index_items(self, items: List[Dict]):
        # use dict unpacking
        # https://stackoverflow.com/questions/31750441/generalised-insert-into-sqlalchemy-using-dictionary
        return

    def check_exists(self, items: List[Dict]) -> List[Dict]:
        return []

