from dataclasses import dataclass
from typing import Type, Dict, Optional, Callable, Tuple

from order_book import OrderBook

from featurizer.features.data.data_definition import Event


@dataclass
class _State:
    timestamp: float
    receipt_timestamp: float
    order_book: OrderBook
    data_inconsistencies: Dict
    depth: Optional[int] = None
    inited: bool = False
    ob_count: int = 0


def cryptotick_update_state(state: _State, event: Event, depth: Optional[int] = None) -> Tuple[_State, bool]:
    # see https://www.cryptotick.com/Faq
    update_type = event['update_type']
    if update_type != 'SNAPSHOT' and not state.inited:
        # bool indicates skip event
        return state, True
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
            if state.order_book[side][price] == 0.0:
                del state.order_book[side][price]
    elif update_type == 'SUB':
        # TODO proper log data inconsistency
        no_keys_for_sub_event = 0
        for side, price, size in event['orders']:
            if price not in state.order_book[side]:
                no_keys_for_sub_event += 1
            else:
                state.order_book[side][price] -= size
                if state.order_book[side][price] == 0.0:
                    del state.order_book[side][price]

        # TODO proper log data inconsistency
        if no_keys_for_sub_event > 0:
            print(f'SUB update_type has {no_keys_for_sub_event} missing keys')
    else:
        raise ValueError(f'Unknown update_type: {update_type}')

    state.timestamp = event['timestamp']
    state.receipt_timestamp = event['receipt_timestamp']

    return state, False


def cryptofeed_update_state(state: _State, event: Event, depth: Optional[int] = None) -> Tuple[_State, bool]:
    if event['delta'] and not state.inited:
        # bool indicates skip event
        return state, True
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
                # TODO proper log data inconsistency
                inconsistency_type = 'no_price_with_zero_size'
                state.data_inconsistencies[inconsistency_type] = state.data_inconsistencies.get(inconsistency_type, 0) + 1
        else:
            state.order_book[side][price] = size

    state.timestamp = event['timestamp']
    state.receipt_timestamp = event['receipt_timestamp']

    return state, False