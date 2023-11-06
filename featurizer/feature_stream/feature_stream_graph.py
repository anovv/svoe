from typing import Dict, Tuple, Callable, List, Any

import streamz
from streamz import Stream

from featurizer.features.feature_tree.feature_tree import Feature, construct_stream_tree
import featurizer.data_definitions.data_definition as data_def


NamedDataEvent = Tuple[Feature, data_def.Event]
# (
#   feature-MidPriceFD-0-4f83d18e, frozendict.frozendict(
#       {'timestamp': 1675216068.340869,
#       'receipt_timestamp': 1675216068.340869,
#       'mid_price': 23169.260000000002})
#  )

# (
#   (feature-MidPriceFD-0-4f83d18e, frozendict.frozendict(
#       {'timestamp': 1675216068.340869,
#       'receipt_timestamp': 1675216068.340869,
#       'mid_price': 23169.260000000002})),
#   (feature-VolatilityStddevFD-0-ad30ace5, frozendict.frozendict(
#       {'timestamp': 1675216068.340869,
#       'receipt_timestamp': 1675216068.340869,
#       'volatility': 0.00023437500931322575}))
#  )
GroupedNamedDataEvent = Tuple[NamedDataEvent, ...]


class FeatureStreamGraph:

    def __init__(self, features: List[Feature], callback: Callable[[GroupedNamedDataEvent], Any]):

        # TODO what happens if we have same features as source and dependency?
        # build data streams trees

        self.data_streams_per_feature: Dict[Feature, Tuple[Stream, Dict[Feature, Stream]]] = {}
        for f in features:
            out, data_streams = construct_stream_tree(f)
            self.data_streams_per_feature[f] = out, data_streams

        out_streams = []
        for feature in features:
            out_stream, _ = self.data_streams_per_feature[feature]
            out_streams.append(out_stream)
        unified_out_stream = streamz.combine_latest(*out_streams)
        unified_out_stream.sink(callback)

    def emit_named_data_event(self, named_event: NamedDataEvent):
        for feature in self.data_streams_per_feature:
            _, data_streams = self.data_streams_per_feature[feature]
            data = named_event[0]
            if data in data_streams:
                data_streams[data].emit(named_event)
