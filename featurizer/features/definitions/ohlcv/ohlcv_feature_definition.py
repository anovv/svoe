from typing import List, Dict, Optional, Any, Tuple, Type

from portion import IntervalDict, closed
from streamz import Stream

from featurizer.features.blocks.blocks import BlockMeta
from featurizer.features.data.data_definition import EventSchema, DataDefinition, Event
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.features.utils import convert_str_to_seconds

from dataclasses import dataclass

import functools
import featurizer.features.definitions.stream_utils as su
import toolz
from datetime import datetime


@dataclass
class _State:
    # TODO do we need both start_ts and last_ts?
    last_ts: Optional[float] = None
    ohlcv: Optional[Dict] = None
    start_ts: Optional[float] = None


class OHLCVFeatureDefinition(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': float,
            'vwap': float,
            'num_trades': int
        }

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [TradesData]

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        state = _State(last_ts=None, ohlcv=None)
        # TODO validate supported windows (only s, m, h)
        # TODO figure out default setting
        window = feature_params.get('window', '1m')
        update = functools.partial(cls._update_state, window=window)
        trades_upstream = toolz.first(upstreams.values())
        acc = trades_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc)

    @classmethod
    def _update_state(cls, state: _State, event: Event, window: str) -> Tuple[_State, Optional[Event]]:
        timestamp = event['timestamp']
        receipt_timestamp = event['receipt_timestamp']
        # for idempotency, skip events before window-based starting point
        if state.start_ts is None:
            # first event
            state.start_ts = cls._get_closest_start_ts(timestamp, window, before=False)

        if timestamp < state.start_ts:
            # skip
            return state, None

        for trade in event['trades']:
            # TODO make trade a dict
            side, amount, price, order_type, trade_id = trade
            # TODO can we make use of order_type and trade_id in OHLCV?
            if state.ohlcv is None:
                state.ohlcv = dict(zip(cls.event_schema().keys(), [timestamp, receipt_timestamp, price, price, price, price, 0, 0, 0]))
            if state.last_ts is None:
                state.last_ts = timestamp

            state.ohlcv['close'] = price
            state.ohlcv['volume'] += amount
            if price > state.ohlcv['high']:
                state.ohlcv['high'] = price
            if price < state.ohlcv['low']:
                state.ohlcv['low'] = price
            state.ohlcv['vwap'] += price * amount

        state.ohlcv['num_trades'] += len(event['trades'])

        # TODO fix here?
        if timestamp - state.last_ts > convert_str_to_seconds(window):
            state.last_ts = timestamp
            state.ohlcv['vwap'] /= state.ohlcv['volume']
            # TODO use start_ts?
            # TODO easier way to state.ohlcv -> frozen_dict: Event ?
            ohlcv = cls.construct_event(timestamp, receipt_timestamp,
                state.ohlcv['open'], state.ohlcv['high'], state.ohlcv['low'], state.ohlcv['close'], state.ohlcv['volume'],
                state.ohlcv['vwap'], state.ohlcv['num_trades']
            )
            state.ohlcv = None # TODO init a new one
            return state, ohlcv
        else:
            return state, None

    # TODO write tests and fix this, this is wrong
    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: 'Feature', dep_feature: 'Feature') -> IntervalDict:
        # TODO we assume no holes here
        # TODO figure out default settings
        window = feature.params.get('window', '1m')
        num_grouped_windows = feature.params.get('num_grouped_windows', 1) # defines group size
        res = cls._group_by_fixed_window(ranges, window, num_grouped_windows)
        print(res)
        return res

    # TODO util this
    @classmethod
    def _group_by_fixed_window(cls, ranges: List[BlockMeta], window: str, num_grouped_windows: int) -> IntervalDict:
        res = IntervalDict()
        first_block_start_ts = ranges[0]['start_ts']
        last_block_end_ts = ranges[-1]['end_ts']
        group_start_ts = cls._get_closest_start_ts(first_block_start_ts, window, before=True)
        # TODO we assume block_size is smaller than window, what if otherwise?
        while group_start_ts <= last_block_end_ts:
            group_end_ts = group_start_ts + num_grouped_windows * convert_str_to_seconds(window)
            group = []
            # TODO this is O(n^2) complexity
            for block_meta in ranges:
                if (group_start_ts <= block_meta['start_ts'] <= group_end_ts and group_start_ts <= block_meta[
                    'end_ts'] <= group_end_ts) \
                        or block_meta['start_ts'] <= group_start_ts <= block_meta['end_ts'] \
                        or block_meta['start_ts'] <= group_end_ts <= block_meta['end_ts']:
                    group.append(block_meta)

            # make sure group is fully covered
            if len(group) != 0 and group[0]['start_ts'] <= group_start_ts and group[-1]['end_ts'] >= group_end_ts:
                res[closed(group_start_ts, group_end_ts)] = group
                group_start_ts = group_end_ts
            else:
                group_start_ts += convert_str_to_seconds(window)

        return res

    # TODO this is for windows no higher then 'h' time_unit, assert that here
    @classmethod
    def _get_closest_start_ts(cls, timestamp: float, window: str, before: bool) -> float:
        dt = datetime.fromtimestamp(timestamp)
        # for idempotency, we assume 00-00:00.00 of the current day as a starting point for splitting data into blocks
        start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        start_ts = start_dt.timestamp()
        window_s = convert_str_to_seconds(window)
        while start_ts + window_s < timestamp:
            start_ts += window_s
        return start_ts if before else start_ts + window_s

    # TODO move this to separate class
    @classmethod
    def _test_grouping(cls):
        ranges = [
            {'start_ts': 2, 'end_ts': 5},
            {'start_ts': 6, 'end_ts': 9},
            {'start_ts': 10, 'end_ts': 13},
            {'start_ts': 14, 'end_ts': 17},
            {'start_ts': 18, 'end_ts': 21},
            {'start_ts': 22, 'end_ts': 25},
            {'start_ts': 26, 'end_ts': 29},
        ]
        window='8s'
        num_grouped_windows = 1

        first_block_start_ts = ranges[0]['start_ts']
        group_start_ts = cls._get_closest_start_ts(first_block_start_ts, window, before=False)
        grouped = cls._group_by_fixed_window(ranges, window, num_grouped_windows)
        assert group_start_ts == 8.0
        assert grouped == IntervalDict({
            closed(8.0, 16.0): [{'start_ts': 6, 'end_ts': 9}, {'start_ts': 10, 'end_ts': 13}, {'start_ts': 14, 'end_ts': 17}],
            closed(16.0, 24.0): [{'start_ts': 14, 'end_ts': 17}, {'start_ts': 18, 'end_ts': 21}, {'start_ts': 22, 'end_ts': 25}]
        })