from typing import Optional, List, Type, Dict, Deque

import toolz
from portion import IntervalDict
from streamz import Stream

from common.streamz.stream_utils import lookback_apply
from featurizer.blocks.blocks import BlockMeta, windowed_grouping
from featurizer.data_definitions.data_definition import EventSchema, DataDefinition, Event
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import Feature


class Diff(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'val': float
        }

    @classmethod
    def dep_upstream_schema(cls, dep_schema: str = Optional[None]) -> List[Type[DataDefinition]]:
        return [FeatureDefinition]

    @classmethod
    def stream(cls, upstreams: Dict[Feature, Stream], feature_params: Dict) -> Stream:
        upstream = toolz.first(upstreams.values())
        window = '1m' # TODO figure out default setting
        if feature_params is not None and 'window' in feature_params:
            window = feature_params['window']
        # TODO sampling
        return lookback_apply(upstream, window, cls._diff_percent)

    @classmethod
    def group_dep_ranges(cls, ranges: List[BlockMeta], feature: Feature, dep_feature: Feature) -> IntervalDict:
        window = '1m'  # TODO figure out default setting
        if feature.params is not None and 'window' in feature.params:
            window = feature.params['window']
        return windowed_grouping(ranges, window)

    @classmethod
    def _diff_percent(cls, values: Deque) -> Event:
        last_value = values[-1]
        first_value = values[0]
        diff = (last_value - first_value)/first_value
        return cls.construct_event(last_value['timestamp'], last_value['receipt_timestamp'], diff)