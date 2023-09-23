import pandas as pd

from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.feature_block_metadata import FeatureBlockMetadata


class DataStoreAdapter:

    def load_df(self, path: str, **kwargs) -> pd.DataFrame:
        raise NotImplementedError

    def store_df(self, path: str, df: pd.DataFrame, **kwargs):
        raise NotImplementedError

    def make_feature_block_path(self, item: FeatureBlockMetadata) -> str:
        raise NotImplementedError

    def make_data_source_block_path(self, item: DataSourceBlockMetadata) -> str:
        raise NotImplementedError

