from typing import List, Dict, Optional, Type

from portion import IntervalDict
from streamz import Stream

from svoe.featurizer.blocks.blocks import BlockMeta, identity_grouping
from svoe.featurizer.features.definitions.feature_definition import FeatureDefinition
from svoe.featurizer.data_definitions.data_definition import DataDefinition, EventSchema
from svoe.featurizer.features.definitions.l2_book.l2_snapshot_fd.l2_snapshot_fd import L2SnapshotFD
from svoe.featurizer.features.feature_tree.feature_tree import Feature

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
    def dep_upstream_schema(cls, dep_schema: Optional[str] = None) -> List[Type[DataDefinition]]:
        return [L2SnapshotFD]

    @classmethod
    def group_dep_ranges(
        cls,
        feature: Feature,
        dep_ranges: Dict[Feature, List[BlockMeta]]
    ) -> IntervalDict:
        ranges = list(dep_ranges.values())[0]
        return identity_grouping(ranges)
