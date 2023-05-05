from typing import List, Dict, Optional, Type
from streamz import Stream
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.data import DataDefinition, EventSchema
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd import L2SnapshotFD
from featurizer.features.feature_tree.feature_tree import Feature

import math
import toolz


class RelativeBidAskSpreadFD(FeatureDefinition):

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

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        return [L2SnapshotFD]

    # TODO grouping
