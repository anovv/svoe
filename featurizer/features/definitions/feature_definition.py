from __future__ import annotations
from streamz import Stream
from typing import Dict, List, Tuple, Union, Type
from ta.utils import dropna
from ta.volatility import BollingerBands
from portion import IntervalDict
from featurizer.features.data.data_definition import DataDefinition, NamedFeature
from featurizer.features.blocks.blocks import BlockMeta
from pandas import DataFrame


# Represents a feature schema to be used with different params (exchanges, symbols, instrument_types, etc)
# each set of params producing materialized feature
class FeatureDefinition(DataDefinition):

    @classmethod
    def named(cls) -> NamedFeature:
        return super(FeatureDefinition, cls).named()

    @classmethod
    def is_data_source(cls) -> bool:
        return False

    # TODO make dep_upstreams: Dict[NamedFeature, Stream]
    @classmethod
    def stream(cls, dep_upstreams: Dict[NamedFeature, Stream]) -> Stream:
        raise NotImplemented

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        # upstream dependencies
        raise NotImplemented

    @classmethod
    def dep_upstream_schema_named(cls) -> List[NamedFeature]:
        # takes care of cases when feature has multiple dependencies of the same type
        res = []
        count_by_type = {}
        for dep in cls.dep_upstream_schema():
            if dep.type_str() in count_by_type:
                res.append((f'{dep.type_str()}-{count_by_type[dep.type_str()]}', dep))
                count_by_type[dep.type_str()] += 1
            else:
                res.append((f'{dep.type_str()}-0', dep))
                count_by_type[dep.type_str()] = 0
        return res

    # TODO we assume no 'holes' in data, use ranges: List[BlockRangeMeta] with holes
    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], dep_named_feature: NamedFeature) -> IntervalDict: # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        # logic to group input data into atomic blocks for bulk processing
        # TODO this should be identity mapping by default?
        raise NotImplemented


# check https://github.com/bukosabino/ta
# check https://github.com/matplotlib/mplfinance
