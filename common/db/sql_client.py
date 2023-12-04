import enum
import os
from typing import Optional, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.db.base import Base

Session = sessionmaker()

SVOE_DB_NAME = 'svoe_db'

DEFAULT_MYSQL_CONFIG = {
    'mysql_user': 'root',
    'mysql_password': '',
    'mysql_host': '127.0.0.1',
    'mysql_port': '3306',
    'mysql_database': SVOE_DB_NAME,
}

SQLITE_DB_PATH = '/tmp/svoe/sqlite'
DUCKDB_DB_PATH = '/tmp/svoe/duckdb'


class DbType(enum.Enum):
    SQLITE = 'sqlite'
    MYSQL = 'mysql'
    DUCKDB = 'duckdb'


def get_db_type() -> str:
    return os.getenv('SVOE_DB_TYPE', DbType.DUCKDB)


def duckdb_connection_string() -> str:
    return f'duckdb:///{DUCKDB_DB_PATH}/{SVOE_DB_NAME}.duckdb'


def sqlite_connection_string() -> str:
    return f'sqlite:///{SQLITE_DB_PATH}/{SVOE_DB_NAME}.db'


def mysql_connection_string(config: Optional[Dict] = None, add_db: bool = True) -> str:
    if config is None:
        config = DEFAULT_MYSQL_CONFIG
    user = os.getenv('MYSQL_USER', config.get('mysql_user'))
    password = os.getenv('MYSQL_PASSWORD', config.get('mysql_password'))
    host = os.getenv('MYSQL_HOST', config.get('mysql_host'))
    port = os.getenv('MYSQL_PORT', config.get('mysql_port'))
    db = os.getenv('MYSQL_DATABASE', config.get('mysql_database'))
    if add_db:
        url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'
    else:
        url = f'mysql+pymysql://{user}:{password}@{host}:{port}'

    return url


def get_conn_str() -> str:
    db_type = get_db_type()
    if db_type == DbType.SQLITE:
        return sqlite_connection_string()
    elif db_type == DbType.MYSQL:
        return mysql_connection_string()
    elif db_type == DbType.DUCKDB:
        return duckdb_connection_string()
    else:
        raise ValueError(f'Unsupported db type: {db_type}')


class SqlClient:

    engine_instance = None

    def __init__(self):
        if SqlClient.engine_instance is None:
            SqlClient.engine_instance = self._init_engine()
            self.engine = SqlClient.engine_instance
        else:
            self.engine = SqlClient.engine_instance

    def _init_engine(self):
        engine = create_engine(get_conn_str(), echo=False)
        Session.configure(bind=engine)
        return engine

    def create_tables_SCRIPT_ONLY(self):
        # creates if not exists
        Base.metadata.create_all(self.engine)
