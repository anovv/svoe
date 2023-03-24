from typing import List, Type, Optional, Tuple

from order_book import OrderBook

from featurizer.features.data.data_definition import DataDefinition, Event
from featurizer.features.data.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import \
    CryptofeedL2BookIncrementalData
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd_base import L2SnapshotFDBase, _State


class CryptofeedL2BookSnapshotFD(L2SnapshotFDBase):

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [CryptofeedL2BookIncrementalData]

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
                    state.data_inconsistencies[inconsistency_type] = state.data_inconsistencies.get(inconsistency_type,
                                                                                                    0) + 1
            else:
                state.order_book[side][price] = size

        state.timestamp = event['timestamp']
        state.receipt_timestamp = event['receipt_timestamp']

        return state, cls._state_snapshot(state, depth)