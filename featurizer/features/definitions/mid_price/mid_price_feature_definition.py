from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definitions.data_models_utils import TimestampedBase
from featurizer.features.definitions.feature_definition import FeatureDefinition

from dataclasses import dataclass


@dataclass # TODO this should be in common classes
class MidPrice(TimestampedBase):
    mid_price: float


class MidPriceFeatureDefinition(FeatureDefinition):

    @staticmethod
    def stream(upstream: Stream) -> Stream:
        return upstream.map(lambda snap: MidPrice(
            timestamp=snap.timestamp,
            receipt_timestamp=snap.receipt_timestamp,
            mid_price=(snap.bids[0][0] + snap.asks[0][0])/2
        ))
