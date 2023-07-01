import functools
from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Optional, Type, Tuple

from portion import IntervalDict
from streamz import Stream
import utils.streamz.stream_utils as su

from featurizer.blocks.blocks import BlockMeta, windowed_grouping
from featurizer.data_definitions.trades.trades import TradesData
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.data_definitions.data_definition import DataDefinition, EventSchema, Event
from featurizer.features.feature_tree.feature_tree import Feature

import toolz

from utils.time.utils import convert_str_to_seconds, get_sampling_bucket_ts


@dataclass
class _State:
    last_sampling_bucket_ts = -1
    queue = deque()
    sell_vol = 0
    buy_vol = 0


class TradeVolumeImbFD(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'tvi': float,
            'dt_ts': float,
        }

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        trades_upstream = toolz.first(upstreams.values())
        window = '1m'  # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        sampling = feature_params.get('sampling', 'raw')
        state = _State()
        window_s = convert_str_to_seconds(window)
        update = functools.partial(cls._update_state, sampling=sampling, window_s=window_s)
        acc = trades_upstream.accumulate(update, returns_state=True, start=state)
        return su.filter_none(acc).unique(maxsize=1)

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        return [TradesData]

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: Feature, dep_feature: Feature) -> IntervalDict:
        window = '1m'  # TODO figure out default setting
        if feature.params is not None and 'window' in feature.params:
            window = feature.params['window']
        return windowed_grouping(ranges, window)

    @classmethod
    def _update_state(cls, state: _State, event: Event, sampling: str, window_s: float) -> Tuple[_State, Optional[Event]]:
        ts = event['timestamp']
        receipt_ts = event['receipt_timestamp']

        # TODO abstraction for time bound queue (similar to lookback_apply)
        state.queue.append(event)
        while ts - state.queue[0]['timestamp'] > window_s:
            e = state.queue.popleft()
            if e['side'] == 'BUY':
                state.buy_vol -= e['price'] * e['amount']
            else:
                state.sell_vol -= e['price'] * e['amount']

        if event['side'] == 'BUY':
            state.buy_vol += event['price'] * event['amount']
        else:
            state.sell_vol += event['price'] * event['amount']

        tvi = 2 * (state.buy_vol - state.sell_vol) / (state.buy_vol + state.sell_vol)

        # buy_vol = 0
        # sell_vol = 0
        # for e in state.queue:
        #     for trade in e['trades']:
        #         if trade['side'] == 'BUY':
        #             buy_vol += trade['price'] * trade['amount']
        #         else:
        #             sell_vol += trade['price'] * trade['amount']
        #
        # avg_vol = (buy_vol + sell_vol)/2
        # tvi = (buy_vol - sell_vol)/avg_vol
        # TODO sampling and event construction should be abstracted out
        if sampling == 'raw':
            return state, cls.construct_event(ts, receipt_ts, tvi, state.last_sampling_bucket_ts)
        else:
            # sampling_s = convert_str_to_seconds(sampling)
            # if state.last_emitted_ts < 0 or ts - state.last_emitted_ts > sampling_s:
            #     state.last_emitted_ts = ts
            #     return state, cls.construct_event(ts, receipt_ts, tvi)
            # else:
            #     return state, None
            sampling_bucket_ts = get_sampling_bucket_ts(ts, sampling)
            if state.last_sampling_bucket_ts != sampling_bucket_ts:
                state.last_sampling_bucket_ts = sampling_bucket_ts
                return state, cls.construct_event(ts, receipt_ts, tvi, sampling_bucket_ts)
            else:
                return state, None


