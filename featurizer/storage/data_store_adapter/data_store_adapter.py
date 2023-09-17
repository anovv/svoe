import pandas as pd

from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.sql.feature_catalog.models import FeatureCatalog


class DataStoreAdapter:

    def load_df(self, path: str, **kwargs) -> pd.DataFrame:
        raise NotImplementedError

    def store_df(self, path: str, df: pd.DataFrame, **kwargs):
        raise NotImplementedError

    def make_feature_catalog_block_path(self, item: FeatureCatalog) -> str:
        raise NotImplementedError

    def make_data_catalog_block_path(self, item: DataCatalog) -> str:
        raise NotImplementedError

