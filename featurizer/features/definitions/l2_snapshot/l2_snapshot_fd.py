from typing import List, Dict, Optional, Tuple, Type

from portion import IntervalDict, closed
from streamz import Stream
from order_book import OrderBook
from frozenlist import FrozenList
from featurizer.data_definitions.data_definition import DataDefinition, Event, EventSchema
from featurizer.data_definitions.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.features.definitions.l2_snapshot.utils import _State, cryptofeed_update_state, cryptotick_update_state
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.features.definitions.feature_definition import FeatureDefinition
import utils.streamz.stream_utils as su
from featurizer.data_definitions.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import CryptofeedL2BookIncrementalData
from featurizer.blocks.blocks import BlockMeta
import functools
import toolz

from utils.time.utils import convert_str_to_seconds


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
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Tuple[Stream, _State]:
        l2_book_deltas_upstream = toolz.first(upstreams.values())
        state = _State(
            timestamp=-1,
            receipt_timestamp=-1,
            order_book=OrderBook(),
            data_inconsistencies={},
        )
        if feature_params is None:
            feature_params = {}

        # TODO dep_schema -> source
        depth = feature_params.get('depth', cls.DEFAULT_DEPTH)
        dep_schema = feature_params.get('dep_schema', None)
        sampling = feature_params.get('sampling', 'raw')

        update = functools.partial(cls._update_state, depth=depth, sampling=sampling, dep_schema=dep_schema)
        acc = l2_book_deltas_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc).unique(maxsize=1), state

    @classmethod
    def _update_state(cls, state: _State, event: Event, depth: int, sampling: str, dep_schema: Optional[str] = None) -> Tuple[_State, Optional[Event]]:
        if dep_schema is None:
            state, skip_event = cryptofeed_update_state(state, event, depth)
        elif dep_schema == 'cryptotick':
            state, skip_event = cryptotick_update_state(state, event, depth)
        else:
            raise ValueError(f'Unsupported dep_schema: {dep_schema}')

        # TODO sampling and event construction should be abstracted out
        # calling cls._state_snapshot(state, depth) on every event is very heavy,
        # 300x slowdown (383.938503742218s vs 1.4724829196929932s for run_stream on 5Gb dataframe)
        if sampling == 'raw':
            return state, None if skip_event else cls._state_snapshot(state, depth)
        elif sampling == 'skip_all':
            return state, None
        else:
            sampling_s = convert_str_to_seconds(sampling)
            if (state.last_emitted_ts < 0 or state.timestamp - state.last_emitted_ts > sampling_s) and not skip_event:
                state.last_emitted_ts = state.timestamp
                return state, cls._state_snapshot(state, depth)
            else:
                return state, None

    @classmethod
    def _state_snapshot(cls, state: _State, depth: int) -> Event:
        bids = FrozenList()
        asks = FrozenList()
        if depth == -1: # indicates full book
            depth = min(len(state.order_book.bids), len(state.order_book.asks))
        else:
            depth = min(depth, min(len(state.order_book.bids), len(state.order_book.asks)))

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
        for r in ranges:
            meta = r['meta']
            if meta_key in meta:
                found_snapshot = True
            if found_snapshot:
                cur_ranges.append(r)
            if meta_key in meta:
                if start_ts is None:
                    start_ts = meta[meta_key][0]
                else:
                    # TODO there will be a 1ts overlap between partitioned groups
                    #  do we need to handle this?
                    end_ts = meta[meta_key][0]
                    res[closed(float(start_ts), float(end_ts))] = cur_ranges
                    start_ts = meta[meta_key][0]
                    cur_ranges = [r]

        if not found_snapshot:
            # no snapshots, return empty
            return res

        # append trailing deltas, last block
        end_ts = ranges[-1]['end_ts']
        interval = closed(float(start_ts), float(end_ts))
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

