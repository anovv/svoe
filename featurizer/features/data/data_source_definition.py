from typing import List
from pandas import DataFrame
from featurizer.features.data.data_definition import DataDefinition


# represents raw datasource
class DataSourceDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return True

