from typing import List, Type, Union, Dict
from streamz import Stream
from featurizer.features.definitions.data_models_utils import TimestampedBase
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data_definition import NamedFeature, DataDefinition
from featurizer.features.definitions.l2_book_snapshot.l2_book_snapshot_feature_definition import L2BookSnapshotFeatureDefinition
from featurizer.features.blocks.blocks import BlockMeta
from featurizer.features.blocks.utils import identity_grouping
from portion import IntervalDict

from dataclasses import dataclass

import toolz

@dataclass # TODO this should be in common classes
class MidPrice(TimestampedBase):
    mid_price: float


class MidPriceFeatureDefinition(FeatureDefinition):

    @classmethod
    def stream(cls, upstreams: Dict[str, Stream]) -> Stream:
        l2_book_snapshots_upstream = toolz.first(upstreams.values())
        return l2_book_snapshots_upstream.map(lambda snap: MidPrice(
            timestamp=snap.timestamp,
            receipt_timestamp=snap.receipt_timestamp,
            mid_price=(snap.bids[0][0] + snap.asks[0][0])/2
        ))

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [L2BookSnapshotFeatureDefinition]

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], dep_named_feature: NamedFeature) -> IntervalDict:  # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        return identity_grouping(ranges)
