from typing import Tuple, Type, List
from pandas import DataFrame


# TODO move this to a separate package
# a base class for raw data sources and derived features
class DataDefinition:

    # TODO define event schema

    @classmethod
    def named(cls) -> Tuple[str, Type]:
        return f'{cls.type_str()}-0', cls

    @classmethod
    def type_str(cls) -> str:
        return cls.__name__

    # this is a hacky way to discern between types in Union[FeatureDefinition, DataSource]
    # without isinstance (due to python bug)
    @classmethod
    def is_data_source(cls) -> bool:
        raise NotImplemented

    @classmethod
    def params(cls):
        raise NotImplemented

    @classmethod
    def parse_events(cls, df: DataFrame) -> List: # TODO typehint
        # TODO implement default behavior
        raise NotImplemented


# TODO come up with a proper base type
# types to represent 'materialized' DataDef/FeatureDef
NamedData = NamedFeature = Tuple[str, Type[DataDefinition]]

