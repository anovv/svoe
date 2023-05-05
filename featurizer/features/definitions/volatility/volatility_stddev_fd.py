from typing import List, Dict, Type, Deque, Optional
from streamz import Stream
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.data import DataDefinition, Event, EventSchema
from featurizer.features.definitions.mid_price.mid_price_fd import MidPriceFD
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.blocks.blocks import BlockMeta, meta_to_interval
from utils.streamz.stream_utils import lookback_apply
from utils.time.utils import convert_str_to_seconds
from portion import IntervalDict

import numpy as np
import toolz


class VolatilityStddevFD(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'volatility': float
        }

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        return [MidPriceFD]

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        mid_price_upstream = toolz.first(upstreams.values())
        window = '1m' # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        return lookback_apply(mid_price_upstream, window, cls._prices_to_volatility)

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: Feature, dep_feature: Feature) -> IntervalDict:
        # TODO util this
        res = IntervalDict()
        # TODO assuming no 'holes' in data
        window = '1m'  # TODO figure out default setting
        if feature.params is not None and 'window' in feature.params:
            window = feature.params['window']
        for i in range(len(ranges)):
            windowed_blocks = [ranges[i]]
            # look back until window limit is reached
            j = i - 1
            while j >= 0 and ranges[i]['start_ts'] - ranges[j]['end_ts'] <= convert_str_to_seconds(window):
                windowed_blocks.append(ranges[j])
                j -= 1
            res[meta_to_interval(ranges[i])] = windowed_blocks

        return res

    @classmethod
    def _prices_to_volatility(cls, prices: Deque) -> Event:
        last_price = prices[-1]
        p = [price['mid_price'] for price in prices]
        stddev = float(np.std(p, dtype=np.float32))
        return cls.construct_event(last_price['timestamp'], last_price['receipt_timestamp'], stddev)
