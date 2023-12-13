import os

import pandas as pd

from svoe.common.pandas.df_utils import load_df_local, store_df_local
from svoe.featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata, build_data_source_block_path
from svoe.featurizer.sql.models.feature_block_metadata import build_feature_block_path, FeatureBlockMetadata
from svoe.featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter
from svoe.featurizer.storage.data_store_adapter.remote_data_store_adapter import SVOE_S3_FEATURE_CATALOG_BLOCK_PATH_PREFIX, \
    SVOE_S3_DATA_CATALOG_BLOCK_PATH_PREFIX

LOCAL_DATA_BLOCKS_DIR = '/tmp/svoe/data_blocks'
LOCAL_FEATURE_CATALOG_BLOCK_PATH_PREFIX = f'{LOCAL_DATA_BLOCKS_DIR}/cataloged_features/'
LOCAL_DATA_CATALOG_BLOCK_PATH_PREFIX = f'{LOCAL_DATA_BLOCKS_DIR}/cataloged_data/'


class LocalDataStoreAdapter(DataStoreAdapter):

    def load_df(self, path: str, **kwargs) -> pd.DataFrame:
        # TODO add warning?
        # in case we use index from remote store for local, paths should be the same,
        # but the prefix is different

        # for data
        if path.startswith(SVOE_S3_DATA_CATALOG_BLOCK_PATH_PREFIX):
            p = path.removeprefix(SVOE_S3_DATA_CATALOG_BLOCK_PATH_PREFIX)
            path = f'{LOCAL_DATA_CATALOG_BLOCK_PATH_PREFIX}{p}'

        # for features
        if path.startswith(SVOE_S3_FEATURE_CATALOG_BLOCK_PATH_PREFIX):
            p = path.removeprefix(SVOE_S3_FEATURE_CATALOG_BLOCK_PATH_PREFIX)
            path = f'{LOCAL_FEATURE_CATALOG_BLOCK_PATH_PREFIX}{p}'

        return load_df_local(path)

    def store_df(self, path: str, df: pd.DataFrame, **kwargs):
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)
        store_df_local(path=path, df=df)

    def make_feature_block_path(self, item: FeatureBlockMetadata) -> str:
        return build_feature_block_path(item=item, prefix=LOCAL_FEATURE_CATALOG_BLOCK_PATH_PREFIX)

    def make_data_source_block_path(self, item: DataSourceBlockMetadata) -> str:
        return build_data_source_block_path(item=item, prefix=LOCAL_DATA_CATALOG_BLOCK_PATH_PREFIX)
