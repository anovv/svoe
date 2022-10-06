from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definition.data_models_utils import TimestampedBase
from featurizer.features.definition.feature_definition import FeatureDefinition

from dataclasses import dataclass
import math


@dataclass
class _RelativeSpread(TimestampedBase):
    spread: float


class RelativeBidAskSpreadFeatureDefinition(FeatureDefinition):

    @staticmethod
    def stream(upstream: Stream) -> Stream:

        return upstream.map(lambda snap: _RelativeSpread(
            timestamp=snap.timestamp,
            receipt_timestamp=snap.receipt_timestamp,
            spread=2 * math.fabs((snap.bids[0][0] - snap.asks[0][0]))/(snap.bids[0][0] + snap.asks[0][0])
        ))
