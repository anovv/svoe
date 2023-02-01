from typing import List, Dict, Optional, Any, Tuple, Type

from portion import IntervalDict
from streamz import Stream

from featurizer.features.blocks.blocks import BlockMeta
from featurizer.features.data.data_definition import EventSchema, DataDefinition, Event
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.features.utils import convert_str_to_seconds

from dataclasses import dataclass

import functools
import featurizer.features.definitions.stream_utils as su
import toolz


@dataclass
class _State:
    last_ts: Optional[float] = None
    ohlcv: Optional[Event] = None


class OHLCVFeatureDefinition(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': float,
            'vwap': float,
            'num_trades': int
        }

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [TradesData]

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        state = _State(last_ts=None, ohlcv=None)
        window = '1m' # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        window_s = convert_str_to_seconds(window)
        update = functools.partial(cls._update_state, window_s=window_s)
        trades_upstream = toolz.first(upstreams.values())
        acc = trades_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc)

    @classmethod
    def _update_state(cls, state: _State, event: Event, window_s: int) -> Tuple[_State, Optional[Event]]:
        timestamp = event['timestamp']
        receipt_timestamp = event['receipt_timestamp']
        for trade in event['trades']:
            # TODO make trade a dict
            side, amount, price, order_type, trade_id = trade
            # TODO can we make use of order_type and trade_id in OHLCV?
            if state.ohlcv is None:
                state.ohlcv = cls.construct_event(timestamp, receipt_timestamp, price, price, price, price, 0, 0, 0)
            if state.last_ts is None:
                state.last_ts = timestamp

            state.ohlcv['close'] = price
            state.ohlcv['volume'] += amount
            if price > state.ohlcv['high']:
                state.ohlcv['high'] = price
            if price < state.ohlcv['low']:
                state.ohlcv['low'] = price
            state.ohlcv['vwap'] += price * amount

        state.ohlcv['num_trades'] += len(event['trades'])

        if timestamp - state.last_ts > window_s:
            state.last_ts = timestamp
            state.ohlcv['vwap'] /= state.ohlcv['volume']
            ohlcv = state.ohlcv.copy()
            state.ohlcv = None
            return state, ohlcv
        else:
            return state, None

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: 'Feature', dep_feature: 'Feature') -> IntervalDict:
        # TODO we assume no holes here
        res = IntervalDict()
        return res
