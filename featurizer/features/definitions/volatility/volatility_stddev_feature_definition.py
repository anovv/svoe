from typing import List, Dict, Optional, Any, Tuple, Type, Deque
from streamz import Stream
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.definitions.mid_price.mid_price_feature_definition import MidPriceFeatureDefinition
from featurizer.features.data.data_definition import DataDefinition, Event, EventSchema
from featurizer.features.feature_tree.feature_tree import FeatureTreeNode
from featurizer.features.blocks.blocks import BlockMeta, get_interval
from featurizer.features.definitions.stream_utils import lookback_apply
from featurizer.features.utils import convert_str_to_seconds

import numpy as np
import toolz


class VolatilityStddevFeatureDefinition(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'volatility': float
        }

    @classmethod
    def dep_upstream_schema(cls) -> List[Type[DataDefinition]]:
        return [MidPriceFeatureDefinition]

    @classmethod
    def stream(cls, upstreams: Dict[FeatureTreeNode, Stream], window: Optional[str] = '1m') -> Stream:
        mid_price_upstream = toolz.first(upstreams.values())
        return lookback_apply(mid_price_upstream, window, cls._prices_to_volatility)

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], dep_feature: FeatureTreeNode) -> IntervalDict:
        # TODO util this
        res = {}
        # TODO assuming no 'holes' in data
        for i in range(len(ranges)):
            window = [ranges[i]]
            # look back until window limit is reached
            j = i - 1
            # TODO pass param
            while j >= 0 and ranges[i]['start_ts'] - ranges[j]['end_ts'] <= convert_str_to_seconds('1m'):
                window.append(ranges[j])
                j -= 1
            res[get_interval(ranges[i])] = window

        return res

    @classmethod
    def _prices_to_volatility(cls, prices: Deque) -> Event:
        last_price = prices[-1]
        p = [price['mid_price'] for price in prices]
        stddev = float(np.std(p, dtype=np.float32))
        return cls.construct_event(last_price['timestamp'], last_price['receipt_timestamp'], stddev)
