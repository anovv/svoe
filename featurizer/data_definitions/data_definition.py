from typing import Type, List, Dict, Any, Tuple

import pandas as pd
from pandas import DataFrame
from frozendict import frozendict
from portion import Interval

from common.pandas.df_utils import is_ts_sorted, hash_df
from diskcache import Cache

from featurizer.blocks.blocks import BlockRangeMeta
from featurizer.features.feature_tree.feature_tree import Feature

PREPROCESSED_DATA_BLOCKS_CACHE = '/tmp/svoe/preprocessed_data_blocks_cache'

Event = Dict[str, Any] # note that this corresponds to raw grouped events by timestamp (only for some data_types, e.g. l2_book_inc)
EventSchema = Dict[str, Type]

NamedDataEvent = Tuple[Feature, Event]
# (
#   feature-MidPriceFD-0-4f83d18e, frozendict.frozendict(
#       {'timestamp': 1675216068.340869,
#       'receipt_timestamp': 1675216068.340869,
#       'mid_price': 23169.260000000002})
#  )

# (
#   (feature-MidPriceFD-0-4f83d18e, frozendict.frozendict(
#       {'timestamp': 1675216068.340869,
#       'receipt_timestamp': 1675216068.340869,
#       'mid_price': 23169.260000000002})),
#   (feature-VolatilityStddevFD-0-ad30ace5, frozendict.frozendict(
#       {'timestamp': 1675216068.340869,
#       'receipt_timestamp': 1675216068.340869,
#       'volatility': 0.00023437500931322575}))
#  )
GroupedNamedDataEvent = Tuple[NamedDataEvent, ...]


def df_to_events(df: DataFrame) -> List[Event]:
    if not is_ts_sorted(df):
        raise ValueError('Unable to parse df with unsorted timestamps')
    return df.to_dict('records')


# TODO move this to a separate package
# a base class for raw data sources and derived features
class DataDefinition:

    # TODO params schema

    # TODO deprecate is_data_source, use isinstance
    # this is a hacky way to discern between types in Union[FeatureDefinition, DataSource]
    # without isinstance (due to python 3.9 bug)
    @classmethod
    def is_data_source(cls) -> bool:
        raise NotImplemented

    # TODO deprecate is_data_source, use isinstance
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
        cache = Cache(PREPROCESSED_DATA_BLOCKS_CACHE)
        if key in cache:
            print(f'[{cls.__name__}] Reading preprocessed df from cache')
            cached_df = cache[key]
            # TODO temp bug fix
            if not isinstance(cached_df, pd.DataFrame):
                print(f'[{cls.__name__}] Malformed df in cache, clearing')
                del cache[key]
            else:
                return cached_df
        res = cls.preprocess_impl(df)
        cache[key] = res
        return res

    @classmethod
    def preprocess_impl(cls, df: DataFrame) -> DataFrame:
        raise NotImplementedError

    @classmethod
    def construct_event(cls, *args) -> Event:
        # TODO validate schema here?
        return frozendict(dict(zip(list(cls.event_schema().keys()), list(args))))

    # TODO when is_synthetic is deprecated this can be in SyntheticDataSourceDefinition
    # for synthetic data
    @classmethod
    def gen_synthetic_events(cls, interval: Interval, params: Dict) -> DataFrame:
        raise NotImplementedError

