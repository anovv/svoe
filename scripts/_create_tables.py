from common.db.sql_client import SqlClient
# these imports are needed for SQLAlchemy to init metadata
from featurizer.sql.models.feature_metadata import FeatureMetadata
from featurizer.sql.models.feature_block_metadata import FeatureBlockMetadata
from featurizer.sql.models.data_source_metadata import DataSourceMetadata
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata

# TODO this are needed only for cloud version
from featurizer.sql.feature_def.models import FeatureDefinitionDB
from svoe_airflow.db.models import DagConfigEncoded


client = SqlClient()
client.create_tables_SCRIPT_ONLY()