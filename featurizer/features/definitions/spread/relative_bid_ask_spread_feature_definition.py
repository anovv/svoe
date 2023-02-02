from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data_definition import DataDefinition, EventSchema
from featurizer.features.feature_tree.feature_tree import Feature

import math
import toolz


class RelativeBidAskSpreadFeatureDefinition(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
           'timestamp': float,
           'receipt_timestamp': float,
           'spread': float
        }

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        mid_price_upstream = toolz.first(upstreams.values())
        return mid_price_upstream.map(lambda snap: cls.construct_event(
            snap['timestamp'],
            snap['receipt_timestamp'],
            2 * math.fabs((snap['bids'][0][0] - snap['asks'][0][0]))/(snap['bids'][0][0] + snap['asks'][0][0])
        ))

    # TODO grouping
