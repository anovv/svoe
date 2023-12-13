from typing import Optional, List, Type, Dict, Deque

import toolz
from portion import IntervalDict
from streamz import Stream

from svoe.common.streamz.stream_utils import lookback_apply
from svoe.featurizer.blocks.blocks import BlockMeta, windowed_grouping
from svoe.featurizer.data_definitions.data_definition import EventSchema, DataDefinition, Event
from svoe.featurizer.features.definitions.feature_definition import FeatureDefinition
from svoe.featurizer.features.feature_tree.feature_tree import Feature


class Diff(FeatureDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'val': float
        }

    @classmethod
    def dep_upstream_schema(cls, dep_schema: Optional[str] = None) -> List[Type[DataDefinition]]:
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
    def _diff_percent(cls, elems: Deque) -> Event:
        last_elem = elems[-1]
        # TODO util this?
        # find value key
        keys = list(last_elem.keys())
        keys.remove('timestamp')
        keys.remove('receipt_timestamp')
        if len(keys) != 1:
            raise ValueError(f'Dependent feature element schema contain multiple values, should be 1')
        key = keys[0]

        last_value = last_elem[key]
        first_value = elems[0][key]
        diff = (last_value - first_value)/first_value
        return cls.construct_event(last_elem['timestamp'], last_elem['receipt_timestamp'], diff)