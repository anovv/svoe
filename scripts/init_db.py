# script to initialize database

import sqlalchemy

# these imports are needed for SQLAlchemy to init metadata
from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.sql.feature_catalog.models import FeatureCatalog

# TODO this are needed only for cloud version
from featurizer.sql.feature_def.models import FeatureDefinitionDB
from svoe_airflow.db.models import DagConfigEncoded


from common.db.sql_client import get_db_type, DbType, mysql_connection_string, SqlClient, SVOE_DB_NAME, \
    sqlite_connection_string

# create mysql database if not exist
if get_db_type() == DbType.MYSQL:
    conn_str = mysql_connection_string(add_db=False)
    with sqlalchemy.create_engine(
        conn_str,
        isolation_level='AUTOCOMMIT'
    ).connect() as connection:
        connection.execute(f'CREATE DATABASE {SVOE_DB_NAME}')
else:
    conn_str = sqlite_connection_string()

# create tables
client = SqlClient(conn_str)
client.create_tables_SCRIPT_ONLY()