from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definitions.data_models_utils import TimestampedBase
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data_definition import DataDefinition
from featurizer.features.feature_tree.feature_tree import Feature

from dataclasses import dataclass
import math
import toolz


@dataclass
class _RelativeSpread(TimestampedBase):
    spread: float


class RelativeBidAskSpreadFeatureDefinition(FeatureDefinition):

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        mid_price_upstream = toolz.first(upstreams.values())
        return mid_price_upstream.map(lambda snap: _RelativeSpread(
            timestamp=snap.timestamp,
            receipt_timestamp=snap.receipt_timestamp,
            spread=2 * math.fabs((snap.bids[0][0] - snap.asks[0][0]))/(snap.bids[0][0] + snap.asks[0][0])
        ))
