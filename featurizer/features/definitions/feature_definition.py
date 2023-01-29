from __future__ import annotations
from streamz import Stream
from typing import Dict, List, Tuple, Union, Type, Any
from ta.utils import dropna
from ta.volatility import BollingerBands
from portion import IntervalDict
from featurizer.features.data.data_definition import DataDefinition
from featurizer.features.feature_tree.feature_tree import FeatureTreeNode
from featurizer.features.blocks.blocks import BlockMeta
from pandas import DataFrame


# Represents a feature schema to be used with different params (exchanges, symbols, instrument_types, etc)
# each set of params producing materialized feature
class FeatureDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return False

    @classmethod
    def stream(cls, dep_upstreams: Dict[FeatureTreeNode, Stream]) -> Stream:
        raise NotImplemented

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        # upstream dependencies
        raise NotImplemented

    # TODO we assume no 'holes' in data, use ranges: List[BlockRangeMeta] with holes
    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], dep_feature: FeatureTreeNode) -> Dict: # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        # logic to group input data into atomic blocks for bulk processing
        # TODO this should be identity mapping by default?
        raise NotImplemented


# check https://github.com/bukosabino/ta
# check https://github.com/matplotlib/mplfinance
