from typing import List
from pandas import DataFrame
from featurizer.features.data.data_definition import DataDefinition, NamedData


# represents raw datasource
class DataSourceDefinition(DataDefinition):

    @classmethod
    def named(cls) -> NamedData:
        return super(DataSourceDefinition, cls).named()

    @classmethod
    def is_data_source(cls) -> bool:
        return True

