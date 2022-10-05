import functools
from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from order_book import OrderBook
import pandas as pd
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from frozenlist import FrozenList
from tqdm import tqdm
import featurizer.features.loader.df_utils as dfu
from featurizer.features.definition.data_models_utils import TimestampedBase
from featurizer.features.definition.feature_definition import FeatureDefinition
import featurizer.features.definition.stream_utils as su
import dask.diagnostics
import distributed.diagnostics
from dask.distributed import progress

@dataclass
class _State(TimestampedBase):
    order_book: OrderBook
    data_inconsistencies: Dict
    depth: Optional[int] = None
    inited: bool = False
    ob_count: int = 0

@dataclass
class _Event(TimestampedBase):
    delta: bool
    orders: List[Tuple[str, float, float]]  # side, price, size


@dataclass(unsafe_hash=True)
class _Snapshot(TimestampedBase):
    timestamp: float = field(compare=False, hash=False)
    receipt_timestamp: float = field(compare=False, hash=False)
    bids: FrozenList[Tuple[float, float]] = field(hash=True)  # price, size
    asks: FrozenList[Tuple[float, float]] = field(hash=True)


# TODO good data 'l2_book', 'BINANCE', 'spot', 'BTC-USDT', '2022-09-29', '2022-09-29'
# TODO remove malformed files
DEFAULT_DEPTH = 1


class L2SnapsFeatureDefinition(FeatureDefinition):

    @staticmethod
    def l2_deltas_to_snaps(deltas: pd.DataFrame) -> Tuple[List[_Snapshot], Dict[str, Any]]:
        # for reverse trnasform snap->delta see https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/util/book.py
        events = L2SnapsFeatureDefinition._parse_events(deltas)

        state = L2SnapsFeatureDefinition._build_state()

        stream = Stream()
        ss = L2SnapsFeatureDefinition._stream(stream, state)
        snapshots = []
        ss.sink(snapshots.append)

        for i in tqdm(range(len(events))):
            stream.emit(events[i])

        return snapshots, state.data_inconsistencies

    @staticmethod
    def stream(upstream: Stream) -> Stream:
        state = L2SnapsFeatureDefinition._build_state()
        return L2SnapsFeatureDefinition._stream(upstream, state)

    @staticmethod
    def _stream(upstream: Stream, state: _State) -> Stream:
        acc = upstream.accumulate(L2SnapsFeatureDefinition._update_state, returns_state=True, start=state)
        return su.filter_none(acc).unique(maxsize=1)
        # return acc.unique(maxsize=1)

    @staticmethod
    def _parse_events(deltas: pd.DataFrame) -> List[_Event]:
        # parses dataframe into list of events
        grouped = deltas.groupby(['timestamp', 'delta'])
        dfs = [grouped.get_group(x) for x in grouped.groups]
        dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
        events = []
        for i in tqdm(range(len(dfs))):
            df = dfs[i]
            timestamp = df.iloc[0].timestamp
            receipt_timestamp = df.iloc[0].receipt_timestamp
            delta = df.iloc[0].delta
            orders = []
            df_dict = df.to_dict(into=OrderedDict, orient='index')
            for v in df_dict.values():
                orders.append((v['side'], v['price'], v['size']))
            events.append(_Event(
                timestamp=timestamp,
                receipt_timestamp=receipt_timestamp,
                delta=delta,
                orders=orders
            ))

        return events

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
            depth=DEFAULT_DEPTH
        )

    @staticmethod
    def _update_state(state: _State, event: _Event) -> Tuple[_State, Optional[_Snapshot]]:
        if event.delta and not state.inited:
            # skip deltas if no snapshot was inited
            return state, None
        if not event.delta:
            # reset order book
            state.inited = True
            state.order_book = OrderBook()
            state.ob_count += 1
        for side, price, size in event.orders:
            if size == 0.0:
                if price in state.order_book[side]:
                    del state.order_book[side][price]
                else:
                    inconsistency_type = 'no_price_with_zero_size'
                    state.data_inconsistencies[inconsistency_type] = state.data_inconsistencies.get(inconsistency_type, 0) + 1
            else:
                state.order_book[side][price] = size

        state.timestamp = event.timestamp
        state.receipt_timestamp = event.receipt_timestamp

        return state, L2SnapsFeatureDefinition._state_snapshot(state)

    @staticmethod
    def _state_snapshot(state: _State) -> _Snapshot:
        bids = FrozenList()
        asks = FrozenList()
        if state.depth is None:
            depth = max(len(state.order_book.bids), len(state.order_book.asks))
        else:
            depth = state.depth

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

        return _Snapshot(
            timestamp=state.timestamp,
            receipt_timestamp=state.receipt_timestamp,
            bids=bids,
            asks=asks
        )

    @staticmethod
    def test():
        files = json.load(open('./test_files.json'))
        files = files[:1]
        df = pd.concat(dfu.load_files(files))
        snaps, inconsistencies = L2SnapsFeatureDefinition.l2_deltas_to_snaps(df)
        print(snaps)
        print(inconsistencies)

