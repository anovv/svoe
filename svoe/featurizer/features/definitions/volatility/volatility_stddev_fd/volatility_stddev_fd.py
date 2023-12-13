from typing import List, Dict, Type, Deque, Optional
from streamz import Stream
from svoe.featurizer.features.definitions.feature_definition import FeatureDefinition
from svoe.featurizer.data_definitions.data_definition import DataDefinition, Event, EventSchema
from svoe.featurizer.features.definitions.price.mid_price_fd.mid_price_fd import MidPriceFD
from svoe.featurizer.features.feature_tree.feature_tree import Feature
from svoe.featurizer.blocks.blocks import BlockMeta, windowed_grouping
from svoe.common.streamz.stream_utils import lookback_apply
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
    def dep_upstream_schema(cls, dep_schema: Optional[str] = None) -> List[Type[DataDefinition]]:
        return [MidPriceFD]

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        mid_price_upstream = toolz.first(upstreams.values())
        window = '1m' # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        # TODO this runs stddev on a whole window on each new event, can we come up with incremental stddev?
        # TODO sampling
        return lookback_apply(mid_price_upstream, window, cls._prices_to_volatility)

    @classmethod
    def group_dep_ranges(
        cls,
        feature: Feature,
        dep_ranges: Dict[Feature, List[BlockMeta]]
    ) -> IntervalDict:
        ranges = list(dep_ranges.values())[0]
        window = '1m'  # TODO figure out default setting
        if feature.params is not None and 'window' in feature.params:
            window = feature.params['window']
        return windowed_grouping(ranges, window)

    @classmethod
    def _prices_to_volatility(cls, prices: Deque) -> Event:
        last_price = prices[-1]
        p = [price['mid_price'] for price in prices]
        stddev = float(np.std(p, dtype=np.float32))
        return cls.construct_event(last_price['timestamp'], last_price['receipt_timestamp'], stddev)
