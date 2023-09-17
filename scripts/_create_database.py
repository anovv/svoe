import os

import sqlalchemy

from common.db.sql_client import get_db_type, DbType, mysql_connection_string, SVOE_DB_NAME, \
    sqlite_connection_string, SQLITE_DB_PATH

# create mysql database if not exist
if get_db_type() == DbType.MYSQL:
    conn_str = mysql_connection_string(add_db=False)
    with sqlalchemy.create_engine(
        conn_str,
        isolation_level='AUTOCOMMIT'
    ).connect() as connection:
        connection.execute(f'CREATE DATABASE {SVOE_DB_NAME}')

elif get_db_type() == DbType.SQLITE:
    os.makedirs(SQLITE_DB_PATH, exist_ok=True)
    conn_str = sqlite_connection_string()
    sqlalchemy.create_engine(conn_str)
