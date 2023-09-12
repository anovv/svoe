from typing import List, Dict

import pandas as pd
from intervaltree import Interval
from pandas import DataFrame

from featurizer.data_definitions.data_definition import Event, DataDefinition

# TODO explore https://stochastic.readthedocs.io/en/stable/
# TODO remove this and DataDefinition, keep only FeatureDefinition?
class SyntheticDataSourceDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return True

    @classmethod
    def is_synthetic(cls) -> bool:
        return True
