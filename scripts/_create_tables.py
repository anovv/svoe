from common.db.sql_client import SqlClient
# these imports are needed for SQLAlchemy to init metadata
from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.sql.feature_catalog.models import FeatureCatalog

# TODO this are needed only for cloud version
from featurizer.sql.feature_def.models import FeatureDefinitionDB
from svoe_airflow.db.models import DagConfigEncoded


client = SqlClient()
client.create_tables_SCRIPT_ONLY()