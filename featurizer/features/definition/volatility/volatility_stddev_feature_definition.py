from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definition.data_models_utils import TimestampedBase
from featurizer.features.definition.feature_definition import FeatureDefinition
from featurizer.features.definition.mid_price.mid_price_feature_definition import _MidPrice

from dataclasses import dataclass

import numpy as np


@dataclass
class _Volatility(TimestampedBase):
    volatility: float


class VolatilityStddevFeatureDefinition(FeatureDefinition):

    @staticmethod
    def stream(upstream: Stream, window_size: int = 1) -> Stream:
        return upstream\
            .sliding_window(window_size, return_partial=False)\
            .map(VolatilityStddevFeatureDefinition._prices_to_volatility)

    @staticmethod
    def _prices_to_volatility(prices: Tuple[_MidPrice]) -> _Volatility:
        last_price = prices[-1]
        p = [price.mid_price for price in prices]
        stddev = float(np.std(p, dtype=np.float32))
        return _Volatility(
            timestamp=last_price.timestamp,
            receipt_timestamp=last_price.receipt_timestamp,
            volatility=stddev
        )
