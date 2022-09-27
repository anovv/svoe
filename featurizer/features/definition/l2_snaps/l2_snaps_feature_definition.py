import functools
from typing import List, Dict, Optional, Any
from streamz import Stream
from order_book import OrderBook
import pandas as pd
from functools import partial
from collections import OrderedDict


# TODO should subclass FeatureDefinition once all fields are figured out
class L2SnapsFeatureDefinition:

    class _State:
        def __init__(self):
            self.order_book = OrderBook()
            self.prev_timestamp = -1
            self.cur_timestamp = -1
            self.data_inconsistencies = {}

    def l2_deltas_to_snaps(self, deltas: pd.DataFrame, depth: Optional[int] = None) -> List[Dict[str, Any]]:
        # for reverse trnasform snap->delta see https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/util/book.py
        updates = deltas.to_dict(into=OrderedDict, orient='index')
        state = self._State()
        snapshots = []
        stream = self._stream(state, snapshots, depth)
        for _, update in updates.items():
            stream.emit(update)

        return snapshots

    def _stream(self, state: _State, snapshots: List, depth: Optional[int] = None):
        stream = Stream()
        stream\
            .accumulate(self._update_state, start=state)\
            .sink(functools.partial(self._append_snapshot, state=state, snapshots=snapshots, depth=depth))

        return stream

    def _update_state(self, state: _State, update: Dict):
        timestamp = update['timestamp']
        side = update['side']
        price = update['price']  # TODO use Decimals?
        size = update['size']
        if size == 0.0:
            if price in state.order_book[side]:
                del state.order_book[side][price]
            else:
                inconsistency_type = 'no_price_with_zero_size'
                state.data_inconsistencies[inconsistency_type] = state.data_inconsistencies.get(inconsistency_type, 0) + 1
        else:
            state.order_book[side][price] = size

        state.prev_timestamp = state.cur_timestamp
        state.cur_timestamp = timestamp

    @staticmethod
    def _order_book_to_snapshot(order_book: OrderBook, depth: Optional[int] = None):
        snapshot = {}

        if depth is None:
            depth = max(len(order_book.bids), len(order_book.asks)) - 1

        for level in range(depth + 1):
            for side in ['bid', 'ask']:
                if side == 'bid':
                    orders = order_book.bids
                else:
                    orders = order_book.asks
                price, size = None, None
                if level < len(orders):
                    price = orders.index(level)[0]
                    size = orders[price]
                snapshot[f'{side}[{level}].price'] = price
                snapshot[f'{side}[{level}].size'] = size

        return snapshot

    def _append_snapshot(self, state: _State, snapshots: List, depth: Optional[int] = None):
        # append only if timestamp has changed
        # (when delta==False each update has same timestamp meaning we reconstruct full order book
        # and we want to snapshot it only when it is fully ready)
        # TODO this will not count full snap, only full snap + first delta

        if state.prev_timestamp == state.cur_timestamp or state.prev_timestamp == -1:
            return

        snapshot = self._order_book_to_snapshot(state.order_book, depth)
        snapshot['timestamp'] = state.cur_timestamp
        snapshots.append(snapshot)

