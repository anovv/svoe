from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definitions.data_models_utils import TimestampedBase
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.definitions.mid_price.mid_price_feature_definition import MidPrice

from dataclasses import dataclass

import numpy as np
import toolz


@dataclass
class _Volatility(TimestampedBase):
    volatility: float


class VolatilityStddevFeatureDefinition(FeatureDefinition):

    @classmethod
    def stream(cls, upstreams: Dict[str, Stream], window_size: int = 1) -> Stream:
        mid_price_upstream = toolz.first(upstreams.values())
        # TODO implement window_over_time or (lookback_window) functionality
        # TODO use rolling()?
        return mid_price_upstream\
            .sliding_window(window_size, return_partial=False)\
            .map(VolatilityStddevFeatureDefinition._prices_to_volatility)

    @staticmethod
    def _prices_to_volatility(prices: Tuple[MidPrice]) -> _Volatility:
        last_price = prices[-1]
        p = [price.mid_price for price in prices]
        stddev = float(np.std(p, dtype=np.float32))
        return _Volatility(
            timestamp=last_price.timestamp,
            receipt_timestamp=last_price.receipt_timestamp,
            volatility=stddev
        )
