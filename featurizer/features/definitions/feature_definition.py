from __future__ import annotations
from streamz import Stream
from typing import Dict, List, Tuple
from ta.utils import dropna
from ta.volatility import BollingerBands
from portion import IntervalDict


# Represent a feature schema to be used with different params (exchanges, symbols, instrument_types, etc)
# each set of params producing materialized feature
class FeatureDefinition:

    @classmethod
    def type(cls) -> str:
        return cls.__name__

    @staticmethod
    def stream(dep_upstreams: Dict[str, Stream]) -> Stream:
        raise ValueError('Not Implemented')

    @staticmethod
    def dep_upstreams_schema() -> List[FeatureDefinition]:
        # upstream dependencies
        raise ValueError('Not Implemented')

    def dep_upstream_schema_named(self) -> List[Tuple[FeatureDefinition, str]]:
        # takes care of cases when feature has multiple dependencies of the same type
        res = []
        count_by_type = {}
        for dep in self.dep_upstreams_schema():
            if dep.type() in count_by_type:
                res.append((dep, f'{dep.type()}-{count_by_type[dep.type()]}'))
                count_by_type[dep.type()] += 1
            else:
                res.append((dep, f'{dep.type()}-0'))
                count_by_type[dep.type()] = 0
        return res

    def group_dep_ranges(self, ranges: List, dep_feature_name: str) -> IntervalDict: # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        # logic to group input data into atomic blocks for bulk processing
        # TODO this should be identity mapping by default
        raise ValueError('Not Implemented')

# check https://github.com/bukosabino/ta
# check https://github.com/matplotlib/mplfinance
