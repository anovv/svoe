from typing import Type, List, Dict, Any
from pandas import DataFrame
from frozendict import frozendict

from common.pandas.df_utils import is_ts_sorted, hash_df
from diskcache import Cache

cache_location = '~/svoe_parsed_events_cache'

Event = Dict[str, Any] # note that this corresponds to raw grouped events by timestamp (only for some data_types, e.g. l2_book_inc)
EventSchema = Dict[str, Type]


# TODO move this to a separate package
# a base class for raw data sources and derived features
class DataDefinition:

    # TODO params schema

    # TODO deprecate is_data_source, us isinstance
    # this is a hacky way to discern between types in Union[FeatureDefinition, DataSource]
    # without isinstance (due to python 3.9 bug)
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
    def parse_events(cls, df: DataFrame) -> List[Event]:
        key = hash_df(df)
        cache = Cache(cache_location)
        if key in cache:
            print(f'[{cls.__name__}] Reading parsed events from cache')
            return cache[key]
        res = cls.parse_events_impl(df)
        cache[key] = res
        return res

    @classmethod
    def parse_events_impl(cls, df: DataFrame) -> List[Event]:
        # TODO validate schema here?
        if not is_ts_sorted(df):
            raise ValueError('Unable to parse df with unsorted timestamps')
        return df.to_dict('records')

    @classmethod
    def construct_event(cls, *args) -> Event:
        # TODO validate schema here?
        return frozendict(dict(zip(list(cls.event_schema().keys()), list(args))))
