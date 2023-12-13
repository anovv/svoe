from svoe.common.db.sql_client import SqlClient
# these imports are needed for SQLAlchemy to init metadata

# TODO this are needed only for cloud version


client = SqlClient()
client.create_tables_SCRIPT_ONLY()