from typing import List, Type, Union, Dict, Optional
from streamz import Stream
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.data.data_definition import DataDefinition, Event, EventSchema
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.features.definitions.l2_snapshot.cryptofeed_l2_snapshot_fd import CryptofeedL2BookSnapshotFD
from featurizer.features.blocks.blocks import BlockMeta
from featurizer.features.blocks.utils import identity_grouping
from portion import IntervalDict
import toolz


class MidPriceFeatureDefinition(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'mid_price': float
        }

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        l2_book_snapshots_upstream = toolz.first(upstreams.values())
        return l2_book_snapshots_upstream.map(
            lambda snap: cls.construct_event(
                snap['timestamp'],
                snap['receipt_timestamp'],
                (snap['bids'][0][0] + snap['asks'][0][0]) / 2,
            )
        )

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [CryptofeedL2BookSnapshotFD]

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: Feature, dep_feature: Feature) -> IntervalDict:  # TODO typehint Block/BlockRange/BlockMeta/BlockRangeMeta
        return identity_grouping(ranges)
