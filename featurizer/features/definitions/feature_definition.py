from __future__ import annotations
from streamz import Stream
from typing import Dict, List, Tuple, Union, Type
from ta.utils import dropna
from ta.volatility import BollingerBands
from portion import IntervalDict
from featurizer.features.data.data import Data
from featurizer.features.blocks.blocks import BlockMeta



# Represent a feature schema to be used with different params (exchanges, symbols, instrument_types, etc)
# each set of params producing materialized feature
class FeatureDefinition:

    @classmethod
    def type_str(cls) -> str:
        return cls.__name__

    # this is a hacky way to discern between types in Union[FeatureDefinition, Data]
    # without isinstance (due to python bug)
    @classmethod
    def is_data(cls) -> bool:
        return False

    @classmethod
    def stream(cls, dep_upstreams: Dict[str, Stream]) -> Stream:
        raise ValueError('Not Implemented')

    @classmethod
    def dep_upstreams_schema(cls) -> List[Type[Union[FeatureDefinition, Data]]]:
        # upstream dependencies
        raise ValueError('Not Implemented')

    @classmethod
    def dep_upstream_schema_named(cls) -> List[Tuple[Type[FeatureDefinition], str]]:
        # takes care of cases when feature has multiple dependencies of the same type
        res = []
        count_by_type = {}
        for dep in cls.dep_upstreams_schema():
            if dep.type_str() in count_by_type:
                res.append((dep, f'{dep.type_str()}-{count_by_type[dep.type_str()]}'))
                count_by_type[dep.type_str()] += 1
            else:
                res.append((dep, f'{dep.type_str()}-0'))
                count_by_type[dep.type_str()] = 0
        return res

    # TODO we assume no 'holes' in data, use ranges: List[BlockRangeMeta] with holes
    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], dep_feature_name: str) -> IntervalDict: # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        # logic to group input data into atomic blocks for bulk processing
        # TODO this should be identity mapping by default?
        raise ValueError('Not Implemented')

# check https://github.com/bukosabino/ta
# check https://github.com/matplotlib/mplfinance
