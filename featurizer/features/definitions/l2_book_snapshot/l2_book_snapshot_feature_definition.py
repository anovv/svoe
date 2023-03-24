from typing import List, Dict, Optional, Tuple, Type

from portion import IntervalDict, closed
from streamz import Stream
from order_book import OrderBook
from dataclasses import dataclass
from frozenlist import FrozenList
from featurizer.features.data.data_definition import DataDefinition, Event, EventSchema
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.features.definitions.feature_definition import FeatureDefinition
import utils.streamz.stream_utils as su
from featurizer.features.data.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import CryptofeedL2BookIncrementalData
from featurizer.features.blocks.blocks import BlockMeta
import functools
import toolz


@dataclass
class _State:
    timestamp: float
    receipt_timestamp: float
    order_book: OrderBook
    data_inconsistencies: Dict
    depth: Optional[int] = None
    inited: bool = False
    ob_count: int = 0

# TODO good data 'l2_book', 'BINANCE', 'spot', 'BTC-USDT', '2022-09-29', '2022-09-29'
# TODO remove malformed files
class L2BookSnapshotFeatureDefinition(FeatureDefinition):

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
        state = cls._build_state()
        depth = 20 # TODO figure out how to set default values
        if feature_params is not None and 'depth' in feature_params:
            depth = feature_params['depth']
        update = functools.partial(cls._update_state, depth=depth)
        acc = l2_book_deltas_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc).unique(maxsize=1)


    # large file BTC-USDT BINANCE spot 2022-09-30
    # s3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-09-30/compaction=raw/version=local/BINANCE*l2_book*BTC-USDT*1664490725.3139572*1664509128.894638*bcf4df95abab48c1a5635a0a95cfaffa.gz.parquet
    # BTC-USDT-PERP BINANCE_FUTURES perpetual 2022-09-30
    # s3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-09-30/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664490725.119688*1664509128.977472*597e77f33f9e43aeaa9c6267eb281ee7.gz.parquet
    @staticmethod
    def _build_state() -> _State:
        return _State(
            timestamp=-1,
            receipt_timestamp=-1,
            order_book=OrderBook(),
            data_inconsistencies={},
        )

    @classmethod
    def _update_state(cls, state: _State, event: Event, depth: Optional[int]) -> Tuple[_State, Optional[Event]]:
        if event['delta'] and not state.inited:
            # skip deltas if no snapshot was inited
            return state, None
        if not event['delta']:
            # reset order book
            state.inited = True
            state.order_book = OrderBook()
            state.ob_count += 1
        for side, price, size in event['orders']:
            if size == 0.0:
                if price in state.order_book[side]:
                    del state.order_book[side][price]
                else:
                    inconsistency_type = 'no_price_with_zero_size'
                    state.data_inconsistencies[inconsistency_type] = state.data_inconsistencies.get(inconsistency_type, 0) + 1
            else:
                state.order_book[side][price] = size

        state.timestamp = event['timestamp']
        state.receipt_timestamp = event['receipt_timestamp']

        return state, cls._state_snapshot(state, depth)

    @classmethod
    def _state_snapshot(cls, state: _State, depth: Optional[int]) -> Event:
        bids = FrozenList()
        asks = FrozenList()
        if depth is None:
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
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [CryptofeedL2BookIncrementalData]

    # @staticmethod
    # def test():
    #     files = json.load(open('./test_files.json'))
    #     files = files[:1]
    #     df = pd.concat(dfu.load_files(files))
    #     snaps, inconsistencies = L2SnapsFeatureDefinition.l2_deltas_to_snaps(df)
    #     print(snaps)
    #     print(inconsistencies)

