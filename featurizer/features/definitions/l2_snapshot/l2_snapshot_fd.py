from typing import List, Dict, Optional, Tuple, Type

from portion import IntervalDict, closed
from streamz import Stream
from order_book import OrderBook
from frozenlist import FrozenList
from featurizer.features.data.data_definition import DataDefinition, Event, EventSchema
from featurizer.features.data.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.features.definitions.l2_snapshot.utils import _State, cryptofeed_update_state, cryptotick_update_state
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.features.definitions.feature_definition import FeatureDefinition
import utils.streamz.stream_utils as su
from featurizer.features.data.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import CryptofeedL2BookIncrementalData
from featurizer.features.blocks.blocks import BlockMeta
import functools
import toolz

# TODO good data 'l2_book', 'BINANCE', 'spot', 'BTC-USDT', '2022-09-29', '2022-09-29'
# TODO remove malformed files
class L2SnapshotFD(FeatureDefinition):

    DEFAULT_DEPTH = 25

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'bids': List[Tuple[float, float]], # price, size
            'asks': List[Tuple[float, float]] # price, size
        }

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        l2_book_deltas_upstream = toolz.first(upstreams.values())
        state = _State(
            timestamp=-1,
            receipt_timestamp=-1,
            order_book=OrderBook(),
            data_inconsistencies={},
        )
        dep_schema = None
        depth = cls.DEFAULT_DEPTH
        if feature_params is not None:
            depth = feature_params.get('depth', depth)
            dep_schema = feature_params.get('dep_schema', None)
        update = functools.partial(cls._update_state, depth=depth, dep_schema=dep_schema)
        acc = l2_book_deltas_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc).unique(maxsize=1)

    @classmethod
    def _update_state(cls, state: _State, event: Event, depth: int, dep_schema: Optional[str] = None) -> Tuple[_State, Optional[Event]]:
        if dep_schema is None:
            state, skip_event = cryptofeed_update_state(state, event, depth)
        elif dep_schema == 'cryptotick':
            state, skip_event = cryptotick_update_state(state, event, depth)
        else:
            raise ValueError(f'Unsupported dep_schema: {dep_schema}')
        return state, None if skip_event else cls._state_snapshot(state, depth)

    @classmethod
    def _state_snapshot(cls, state: _State, depth: int) -> Event:
        bids = FrozenList()
        asks = FrozenList()
        if depth == -1: # indicates full book
            depth = max(len(state.order_book.bids), len(state.order_book.asks))

        for level in range(depth):
            for side in ['bid', 'ask']:
                if side == 'bid':
                    orders = state.order_book.bids
                else:
                    orders = state.order_book.asks
                price, size = None, None
                if level < len(orders):
                    price = orders.index(level)[0]
                    size = orders[price]
                if side == 'bid':
                    bids.append((price, size))
                else:
                    asks.append((price, size))

        bids.freeze()
        asks.freeze()

        return cls.construct_event(state.timestamp, state.receipt_timestamp, bids, asks)

    # TODO test this
    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: Feature, dep_feature: Feature) -> IntervalDict:
        # TODO separate const for this
        # TODO or separate function for metadata parsing
        meta_key = 'snapshot_ts'
        res = IntervalDict()
        # TODO we assume no holes in data here
        start_ts, end_ts = None, None
        found_snapshot = False
        cur_ranges = []
        for meta in ranges:
            if meta_key in meta:
                found_snapshot = True
            if found_snapshot:
                cur_ranges.append(meta)
            if meta_key in meta:
                if start_ts is None:
                    start_ts = meta[meta_key]
                else:
                    # TODO there will be a 1ts overlap between partitioned groups
                    #  do we need to handle this?
                    end_ts = meta[meta_key]
                    res[closed(start_ts, end_ts)] = cur_ranges
                    start_ts = meta[meta_key]
                    cur_ranges = [meta]

        if not found_snapshot:
            # no snapshots, return empty
            return res

        # append trailing deltas, last block
        end_ts = ranges[-1]['end_ts']
        interval = closed(start_ts, end_ts)
        if len(cur_ranges) != 0 and interval not in res:
            res[interval] = cur_ranges

        return res

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        if dep_schema is None:
            return [CryptofeedL2BookIncrementalData]

        if dep_schema == 'cryptotick':
            return [CryptotickL2BookIncrementalData]

        raise ValueError(f'Unknown dep_schema: {dep_schema}')
