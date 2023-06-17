from __future__ import annotations
from streamz import Stream
from typing import Dict, List, Tuple, Union, Type, Any, Optional
from portion import IntervalDict

from featurizer.blocks.blocks import BlockMeta
from featurizer.data_definitions.data_definition import DataDefinition
from featurizer.utils.definitions_loader import DefinitionsLoader


# TODO figure out relationship between Feature and FeatureDefinition (i.e. common interface, subclassing?)
# Represents a feature schema to be used with different params (exchanges, symbols, instrument_types, etc)
# each set of params producing materialized feature
class FeatureDefinition(DataDefinition):
    # TODO params schema

    @classmethod
    def is_data_source(cls) -> bool:
        return False

    @classmethod
    def stream(cls, dep_upstreams: Dict['Feature', Stream], feature_params: Dict) -> Union[Stream, Tuple[Stream, Any]]:
        raise NotImplemented

    # TODO make dep_schema part of feature_params
    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[str]:
        # upstream dependencies
        raise NotImplemented

    @classmethod
    def dep_upstream_definitions(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        return Loader.load_definitions(cls.dep_upstream_schema(dep_schema=dep_schema))

    # TODO we assume no 'holes' in data, use ranges: List[BlockRangeMeta] with holes
    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: 'Feature', dep_feature: 'Feature') -> IntervalDict: # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        # logic to group input data into atomic blocks for bulk processing
        # TODO this should be identity mapping by default?
        raise NotImplemented


# check https://github.com/bukosabino/ta
# check https://github.com/matplotlib/mplfinance
# check https://github.com/twopirllc/pandas-ta
# check https://vectorbt.dev/getting-started/features/#data
# check https://github.com/Kismuz/btgym
# check https://github.com/mementum/backtrader
# check https://github.com/quantopian/zipline
# check https://github.com/mhallsmoore/qstrader
# check https://github.com/saeed349/Microservices-Based-Algorithmic-Trading-System
# check https://nestedsoftware.com/2019/09/26/incremental-average-and-standard-deviation-with-sliding-window-470k.176143.html
# check https://github.com/freqtrade/freqtrade

# http://alkaline-ml.com/pmdarima/

# https://kernc.github.io/backtesting.py/

# https://tulipindicators.org/