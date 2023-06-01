from typing import List, Dict, Optional, Type, Deque

import numpy as np
from portion import IntervalDict
from streamz import Stream

from featurizer.blocks.blocks import BlockMeta, windowed_grouping
from featurizer.data_definitions.trades.trades import TradesData
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.data_definitions.data_definition import DataDefinition, EventSchema, Event
from featurizer.features.feature_tree.feature_tree import Feature

import math
import toolz

from utils.streamz.stream_utils import lookback_apply


class TradeVolumeImbFD(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
           'timestamp': float,
           'receipt_timestamp': float,
           'tvi': float
        }

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        trades_upstream = toolz.first(upstreams.values())
        window = '1m'  # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        sampling = feature_params.get('sampling', 'raw')
        # TODO sampling

        # TODO this can be optimized
        return lookback_apply(trades_upstream, window, cls._tvi)

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        return [TradesData]

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: Feature, dep_feature: Feature) -> IntervalDict:
        window = '1m'  # TODO figure out default setting
        if feature.params is not None and 'window' in feature.params:
            window = feature.params['window']
        return windowed_grouping(ranges, window)

    @classmethod
    def _tvi(cls, trades: Deque) -> Event:
        last_trade = trades[-1]
        buy_vol = float(np.sum([trade['price'] * trade['amount'] if trade['side'] == 'BUY' else 0 for trade in trades], dtype=np.float32))
        sell_vol = float(np.sum([trade['price'] * trade['amount'] if trade['side'] == 'SELL' else 0 for trade in trades], dtype=np.float32))
        avg_vol = (buy_vol + sell_vol)/2
        immbalance = (buy_vol - sell_vol)/avg_vol
        return cls.construct_event(last_trade['timestamp'], last_trade['receipt_timestamp'], immbalance)
