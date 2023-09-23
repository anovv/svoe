import pandas as pd

from common.s3.s3_utils import load_df_s3, store_df_s3
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata, build_data_source_block_path
from featurizer.sql.models.feature_block_metadata import FeatureBlockMetadata, build_feature_block_path
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter

SVOE_S3_FEATURE_CATALOG_BUCKET = 'svoe-feature-catalog-data'
SVOE_S3_FEATURE_CATALOG_BLOCK_PATH_PREFIX = f's3://{SVOE_S3_FEATURE_CATALOG_BUCKET}/'

SVOE_S3_CATALOGED_DATA_BUCKET = 'svoe-cataloged-data'
SVOE_S3_DATA_CATALOG_BLOCK_PATH_PREFIX = f's3://{SVOE_S3_CATALOGED_DATA_BUCKET}/'


class RemoteDataStoreAdapter(DataStoreAdapter):

    def load_df(self, path: str, **kwargs) -> pd.DataFrame:
        return load_df_s3(path)

    def store_df(self, path: str, df: pd.DataFrame, **kwargs):
        store_df_s3(path=path, df=df)

    def make_feature_block_path(self, item: FeatureBlockMetadata) -> str:
        return build_feature_block_path(item=item, prefix=SVOE_S3_FEATURE_CATALOG_BLOCK_PATH_PREFIX)

    def make_data_source_block_path(self, item: DataSourceBlockMetadata) -> str:
        return build_data_source_block_path(item=item, prefix=SVOE_S3_DATA_CATALOG_BLOCK_PATH_PREFIX)

