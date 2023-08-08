import os
from typing import Optional, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.db.base import Base

Session = sessionmaker()


DEFAULT_CONFIG = {
    'mysql_user': 'root',
    'mysql_password': '',
    'mysql_host': '127.0.0.1',
    'mysql_port': '3306',
    'mysql_database': 'svoe_db',
}


class MysqlClient:

    engine_instance = None

    def __init__(self, config: Optional[Dict] = None):
        self.config = config
        if self.config is None:
            self.config = DEFAULT_CONFIG
        if MysqlClient.engine_instance is None:
            MysqlClient.engine_instance = self._init_engine()
            self.engine = MysqlClient.engine_instance
        else:
            self.engine = MysqlClient.engine_instance

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

    # TODO this should not be used, migrate table management to Alembic
    def create_tables(self):
        # creates if not exists
        Base.metadata.create_all(self.engine)