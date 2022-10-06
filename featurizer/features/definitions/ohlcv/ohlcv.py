from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definitions.data_models_utils import TimestampedBase
from featurizer.features.definitions.feature_definition import FeatureDefinition

from dataclasses import dataclass


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
class _State(TimestampedBase):
    last_ts: float
    # TODO


class OHLCVFeatureDefinition(FeatureDefinition):

    @staticmethod
    def stream(upstream: Stream, window='1m') -> Stream:

        # return upstream.map(lambda snap: _MidPrice(
        #     timestamp=snap.timestamp,
        #     receipt_timestamp=snap.receipt_timestamp,
        #     mid_price=(snap.bids[0][0] + snap.asks[0][0])/2
        # ))
        return upstream # TODO

    # def
