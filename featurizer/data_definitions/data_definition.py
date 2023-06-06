from typing import Tuple, Type, List, Dict, Any
from pandas import DataFrame
from frozendict import frozendict

from utils.pandas.df_utils import is_ts_sorted

Event = Dict[str, Any] # note that this corresponds to raw grouped events by timestamp
EventSchema = Dict[str, Type]


# TODO move this to a separate package
# a base class for raw data sources and derived features
class DataDefinition:

    # TODO params schema

    # this is a hacky way to discern between types in Union[FeatureDefinition, DataSource]
    # without isinstance (due to python bug)
    @classmethod
    def is_data_source(cls) -> bool:
        raise NotImplemented

    @classmethod
    def event_schema(cls) -> EventSchema:
        raise NotImplemented

    @classmethod
    def params(cls):
        raise NotImplemented

    @classmethod
    def parse_events(cls, df: DataFrame, **kwargs) -> List[Event]:
        # TODO validate schema here?
        if not is_ts_sorted(df):
            raise ValueError('Unable to parse df with unsorted timestamps')
        return df.to_dict('records')

    @classmethod
    def construct_event(cls, *args) -> Event:
        # TODO validate schema here?
        return frozendict(dict(zip(list(cls.event_schema().keys()), list(args))))


# TODO come up with a proper base type
# types to represent 'materialized' DataDef/FeatureDef
# NamedData = NamedFeature = Tuple[str, Type[DataDefinition]]
