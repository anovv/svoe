import functools
from typing import Dict, Tuple, Callable, List, Any, Union, Optional

import streamz
from streamz import Stream

from featurizer.config import FeaturizerConfig
from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature, construct_features_from_configs

NamedDataEvent = Tuple[Feature, Event]
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


class FeatureStreamNode:

    def __init__(self, feature: Feature, stream: Stream):
        self._feature = feature
        self._stream = stream

    def __hash__(self):
        return hash(self._feature)

    def __eq__(self, other):
        return self._feature == other.get_feature()

    def get_feature(self) -> Feature:
        return self._feature

    def get_stream(self) -> Stream:
        return self._stream


def _connect_stream_graph(features: List[Feature], callbacks: Dict[Feature, Callable[[Feature, Event], Optional[Any]]]) -> Dict[Feature, FeatureStreamNode]:
    existing_nodes = {}
    for feature in features:
        _connect_stream_tree(feature, existing_nodes, callbacks)

    return existing_nodes


def _connect_stream_tree(feature: Feature, exisitng_nodes: Dict[Feature, FeatureStreamNode], callbacks: Dict[Feature, Callable[[Feature, Event], Optional[Any]]]) -> FeatureStreamNode:
    if feature.children is None or len(feature.children) == 0:
        if feature not in exisitng_nodes:
            source = Stream()
            if callbacks is not None and feature in callbacks:
                sink_callable = functools.partial(callbacks[feature], feature)
                source.sink(sink_callable)
            node = FeatureStreamNode(feature, source)
            exisitng_nodes[feature] = node
            return node
        else:
            return exisitng_nodes[feature]
    # upstreams = {dep_feature: Stream() for dep_feature in deps.keys()}
    upstreams = {}
    for child in feature.children:
        stream_node = _connect_stream_tree(child, exisitng_nodes, callbacks)
        stream = stream_node.get_stream()
        upstreams[child] = stream

    if feature in exisitng_nodes:
        return exisitng_nodes[feature]

    # TODO unify feature_definition.stream return type
    s = feature.data_definition.stream(upstreams, feature.params)
    if isinstance(s, Tuple):
        out_stream = s[0]
        state = s[1]
    else:
        out_stream = s
    if callbacks is not None and feature in callbacks:
        sink_callable = functools.partial(callbacks[feature], feature)
        out_stream.sink(sink_callable)
    node = FeatureStreamNode(feature, out_stream)
    exisitng_nodes[feature] = node
    return node


class FeatureStreamGraph:

    def __init__(
        self,
        features_or_config: Union[List[Feature], FeaturizerConfig],
        combine_outputs: bool = False,
        combined_out_callback: Optional[Callable[[GroupedNamedDataEvent], Any]] = None
    ):

        if isinstance(features_or_config, list):
            features = features_or_config
        else:
            config = features_or_config
            features = construct_features_from_configs(config.feature_configs)

        self.features = features
        self.feature_stream_nodes: Dict[Feature, FeatureStreamNode] = _connect_stream_graph(self.features, {})

        if combine_outputs:
            out_streams = []
            for feature in self.features:
                out_streams.append(self.feature_stream_nodes[feature].get_stream())
            unified_out_stream = streamz.combine_latest(*out_streams)
            unified_out_stream.sink(combined_out_callback)

    def __hash__(self):
        return hash(frozenset(self.features))

    def __eq__(self, other):
        return frozenset(self.features) == frozenset(other.features)

    def emit_named_data_event(self, named_event: NamedDataEvent):
        f = named_event[0]
        self.feature_stream_nodes[f].emit(named_event)

    def get_stream(self, feature: Feature) -> Stream:
        return self.feature_stream_nodes[feature].get_stream()

    def set_callback(self, feature: Feature, callback: Callable[[Feature, Event], Optional[Any]]):
        sink_callable = functools.partial(callback, feature)
        self.feature_stream_nodes[feature].get_stream().sink(sink_callable)

    def get_ins(self) -> List[Feature]:
        ins = []
        for feature in self.feature_stream_nodes:
            if feature.children is None or len(feature.children) == 0:
                ins.append(feature)
        if len(ins) == 0:
            raise RuntimeError('Feature graph should have input nodes')
        return ins

    def get_outs(self) -> List[Feature]:
        return self.features


FeatureStreamGroupGraph = Dict[FeatureStreamGraph, List[FeatureStreamGraph]]