from typing import List, Type, Optional, Tuple

from order_book import OrderBook

from featurizer.features.data.data_definition import DataDefinition, Event
from featurizer.features.data.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd_base import L2SnapshotFDBase, _State


class CryptotickL2BookSnapshotFD(L2SnapshotFDBase):

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [CryptotickL2BookIncrementalData]

    @classmethod
    def _update_state(cls, state: _State, event: Event, depth: Optional[int]) -> Tuple[_State, Optional[Event]]:
        # see https://www.cryptotick.com/Faq
        update_type = event['update_type']
        if update_type != 'SNAPSHOT' and not state.inited:
            # skip updates if no snapshot was inited
            return state, None
        if update_type == 'SNAPSHOT':
            # reset order book
            state.inited = True
            state.order_book = OrderBook()
            state.ob_count += 1
        if update_type == 'ADD' or update_type == 'SNAPSHOT':
            for side, price, size in event['orders']:
                if price in state.order_book[side]:
                    state.order_book[side][price] += size
                else:
                    state.order_book[side][price] = size
        elif update_type == 'SET':
            for side, price, size in event['orders']:
                state.order_book[side][price] = size
        elif update_type == 'SUB':
            for side, price, size in event['orders']:
                state.order_book[side][price] -= size
        else:
            raise ValueError(f'Unknown update_type: {update_type}')

        state.timestamp = event['timestamp']
        state.receipt_timestamp = event['receipt_timestamp']

        return state, cls._state_snapshot(state, depth)