from typing import Type, List, Dict, Any

from intervaltree import Interval
from pandas import DataFrame
from frozendict import frozendict

from common.pandas.df_utils import is_ts_sorted, hash_df
from diskcache import Cache

cache_location = '~/svoe_parsed_events_cache'

Event = Dict[str, Any] # note that this corresponds to raw grouped events by timestamp (only for some data_types, e.g. l2_book_inc)
EventSchema = Dict[str, Type]

def df_to_events(df: DataFrame) -> List[Event]:
    if not is_ts_sorted(df):
        raise ValueError('Unable to parse df with unsorted timestamps')
    return df.to_dict('records')


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
    def is_synthetic(cls) -> bool:
        raise NotImplemented

    @classmethod
    def event_schema(cls) -> EventSchema:
        raise NotImplemented

    @classmethod
    def params(cls):
        raise NotImplemented

    @classmethod
    def preprocess(cls, df: DataFrame) -> DataFrame:
        key = hash_df(df)
        cache = Cache(cache_location)
        if key in cache:
            print(f'[{cls.__name__}] Reading parsed events from cache')
            return cache[key]
        res = cls.preprocess_impl(df)
        cache[key] = res
        return res

    @classmethod
    def preprocess_impl(cls, df: DataFrame) -> DataFrame:
        # TODO validate schema here?
        raise NotImplementedError

    @classmethod
    def construct_event(cls, *args) -> Event:
        # TODO validate schema here?
        return frozendict(dict(zip(list(cls.event_schema().keys()), list(args))))

    # for synthetic data
    @classmethod
    def gen_events(cls, interval: Interval, params: Dict) -> DataFrame:
        raise NotImplementedError
