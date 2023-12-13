from typing import List, Type, Dict, Optional
from streamz import Stream

from svoe.featurizer.data_definitions.common.ticker.cryptofeed.cryptofeed_ticker import CryptofeedTickerData
from svoe.featurizer.features.definitions.feature_definition import FeatureDefinition
from svoe.featurizer.data_definitions.data_definition import DataDefinition, EventSchema
from svoe.featurizer.features.definitions.l2_book.l2_snapshot_fd.l2_snapshot_fd import L2SnapshotFD
from svoe.featurizer.features.feature_tree.feature_tree import Feature
from svoe.featurizer.blocks.blocks import BlockMeta, identity_grouping
from portion import IntervalDict
import toolz


class MidPriceFD(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'mid_price': float
        }

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        # TODO proper pass dep_schema
        first_feature: Feature = toolz.first(upstreams.keys())
        first_upstream = toolz.first(upstreams.values())
        if first_feature.data_definition == L2SnapshotFD:
            l2_book_snapshots_upstream = first_upstream
            return l2_book_snapshots_upstream.map(
                lambda snap: cls.construct_event(
                    snap['timestamp'],
                    snap['receipt_timestamp'],
                    (snap['bids'][0][0] + snap['asks'][0][0]) / 2,
                )
            )
        elif first_feature.data_definition == CryptofeedTickerData:
            ticker_upstream = first_upstream
            return ticker_upstream.map(
                lambda ticker: cls.construct_event(
                    ticker['timestamp'],
                    ticker['receipt_timestamp'],
                    (ticker['bid'] + ticker['ask']) / 2,
                )
            )
        else:
            raise ValueError(f'Unsupported dep_schema for upstream def {first_feature.data_definition}')


    @classmethod
    def dep_upstream_schema(cls, dep_schema: Optional[str] = None) -> List[Type[DataDefinition]]:
        if dep_schema is None or dep_schema == 'l2_book':
            return [L2SnapshotFD]
        elif dep_schema == 'ticker':
            return [CryptofeedTickerData]
        else:
            raise ValueError('Unsupported dep_schema')

    @classmethod
    def group_dep_ranges(
        cls,
        feature: Feature,
        dep_ranges: Dict[Feature, List[BlockMeta]]
    ) -> IntervalDict:
        ranges = list(dep_ranges.values())[0]
        return identity_grouping(ranges)
