import functools
from typing import List, Dict, Optional, Any, Tuple
from streamz import Stream
from order_book import OrderBook
import pandas as pd
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class _State:
    order_book: OrderBook
    timestamp: float
    receipt_timestamp: float
    data_inconsistencies: Dict


@dataclass
class _Event:
    timestamp: float
    receipt_timestamp: float
    delta: bool
    orders: List[Tuple[str, float, float]]  # side, price, size


@dataclass
class _Snapshot:
    timestamp: float
    receipt_timestamp: float
    bids_and_asks: Dict[str, float]


# TODO should subclass FeatureDefinition once all fields are figured out
class L2SnapsFeatureDefinition:

    def l2_deltas_to_snaps(self, deltas: pd.DataFrame, depth: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        # for reverse trnasform snap->delta see https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/util/book.py
        updates = deltas.to_dict(into=OrderedDict, orient='index')
        state = _State(OrderBook(), -1, -1, {})
        snapshots = []
        stream = self._stream(state, snapshots, depth)
        for _, update in updates.items():
            stream.emit(update)

        return snapshots, state.data_inconsistencies

    def _get_common_columns(self, deltas: pd.DataFrame) -> Dict[str, Any]:
        # returns columns and values which should be appended to output df
        # i.e. date, symbol, exchange, etc.
        return {} # TODO

    def _parse_events(self, deltas: pd.DataFrame) -> List[_Event]:
        # parses dataframe into list of events
        grouped_by_ts = deltas.groupby('timestamp')
        dfs = [grouped_by_ts.get_group(x) for x in grouped_by_ts.groups]
        events = []
        for df in dfs:
            timestamp = df.iloc[0].timestamp
            receipt_timestamp = df.iloc[0].receipt_timestamp
            delta = df.iloc[0].delta
            orders = []
            df_dict = df.to_dict(into=OrderedDict, orient='index')
            for v in df_dict.values():
                orders.append((v['side'], v['price'], v['size']))
            events.append(_Event(timestamp, receipt_timestamp, delta, orders))

        return events

    def _stream(self, state: _State, snapshots: List, depth: Optional[int] = None):
        stream = Stream()\
            .accumulate(self._update_state, start=state)\
            .map(functools.partial(self._state_snapshot, depth=depth))
            # .sink(functools.partial(self._append_snapshot, state=state, snapshots=snapshots, depth=depth))

        return stream

    @staticmethod
    def _update_state(state: _State, event: _Event):
        if not event.delta:
            # reset order book
            state.order_book = OrderBook()
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

    @staticmethod
    def _state_snapshot(state: _State, depth: Optional[int] = None) -> _Snapshot:
        bids_and_asks = {}
        if depth is None:
            depth = max(len(state.order_book.bids), len(state.order_book.asks)) - 1

        for level in range(depth + 1):
            for side in ['bid', 'ask']:
                if side == 'bid':
                    orders = state.order_book.bids
                else:
                    orders = state.order_book.asks
                price, size = None, None
                if level < len(orders):
                    price = orders.index(level)[0]
                    size = orders[price]
                bids_and_asks[f'{side}[{level}].price'] = price
                bids_and_asks[f'{side}[{level}].size'] = size

        return _Snapshot(state.timestamp, state.receipt_timestamp, bids_and_asks)
