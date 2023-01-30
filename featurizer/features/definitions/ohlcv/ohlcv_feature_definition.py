from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definitions.data_models_utils import TimestampedBase
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import Feature

from featurizer.features.definitions.data_models_utils import Trade
from featurizer.features.utils import convert_str_to_seconds

from dataclasses import dataclass

import functools
import featurizer.features.definitions.stream_utils as su
import toolz


@dataclass
class OHLCV(TimestampedBase):
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float
    num_trades: int


@dataclass
class _State:
    last_ts: Optional[float] = None
    ohlcv: Optional[OHLCV] = None


class OHLCVFeatureDefinition(FeatureDefinition):

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        state = _State(last_ts=None, ohlcv=None)
        window = '1m' # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        window_s = convert_str_to_seconds(window)
        update = functools.partial(OHLCVFeatureDefinition._update_state, window_s=window_s)
        trades_upstream = toolz.first(upstreams.values())
        acc = trades_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc)

    @staticmethod
    def _update_state(state: _State, trade: Trade, window_s: int) -> Tuple[_State, Optional[OHLCV]]:
        if state.ohlcv is None:
            state.ohlcv = OHLCV(
                timestamp=trade.timestamp,
                receipt_timestamp=trade.receipt_timestamp,
                open=trade.price,
                high=trade.price,
                low=trade.price,
                close=trade.price,
                volume=0,
                vwap=0,
                num_trades=0,
            )
        if state.last_ts is None:
            state.last_ts = trade.timestamp

        state.ohlcv.close = trade.price
        state.ohlcv.volume += trade.amount
        if trade.price > state.ohlcv.high:
            state.ohlcv.high = trade.price
        if trade.price < state.ohlcv.low:
            state.ohlcv.low = trade.price
        state.ohlcv.vwap += trade.price * trade.amount
        state.ohlcv.num_trades += 1

        if trade.timestamp - state.last_ts > window_s:
            state.last_ts = trade.timestamp
            state.ohlcv.vwap /= state.ohlcv.volume
            ohlcv = state.ohlcv.copy()
            state.ohlcv = None
            return state, ohlcv
        else:
            return state, None


