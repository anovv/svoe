from typing import List, Dict

import pandas as pd
from intervaltree import Interval
from pandas import DataFrame

from featurizer.data_definitions.data_definition import Event, DataDefinition


# TODO remove this and DataDefinition, keep only FeatureDefinition?
class SyntheticDataSourceDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return True

    @classmethod
    def is_synthetic(cls) -> bool:
        return True

    @classmethod
    def gen_events(cls, interval: Interval, params: Dict) -> pd.DataFrame:
        raise NotImplementedError

    @classmethod
    def parse_events(cls, df: DataFrame) -> List[Event]:
        # this should not be used for synthetic data
        raise NotImplementedError