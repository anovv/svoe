import pandas as pd

from common.s3.s3_utils import load_df_s3, store_df_s3
from featurizer.sql.data_catalog.models import DataCatalog, build_data_catalog_block_path
from featurizer.sql.feature_catalog.models import FeatureCatalog, build_feature_catalog_block_path
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

    def make_feature_catalog_block_path(self, item: FeatureCatalog) -> str:
        return build_feature_catalog_block_path(item=item, prefix=SVOE_S3_FEATURE_CATALOG_BLOCK_PATH_PREFIX)

    def make_data_catalog_block_path(self, item: DataCatalog) -> str:
        return build_data_catalog_block_path(item=item, prefix=SVOE_S3_DATA_CATALOG_BLOCK_PATH_PREFIX)

