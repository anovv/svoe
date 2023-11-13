from typing import Dict, Tuple, Callable, List, Any, Union

import streamz
from streamz import Stream

from featurizer.config import FeaturizerConfig
from featurizer.data_definitions.data_definition import GroupedNamedDataEvent, NamedDataEvent
from featurizer.features.feature_tree.feature_tree import Feature, construct_stream_tree


class FeatureStreamGraph:

    def __init__(
        self,
        features_or_config: Union[List[Feature], FeaturizerConfig],
        out_callback: Callable[[GroupedNamedDataEvent], Any]
    ):

        if isinstance(features_or_config, list):
            features = features_or_config
        else:
            # TODO
            raise NotImplementedError

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
        unified_out_stream.sink(out_callback)

    def emit_named_data_event(self, named_event: NamedDataEvent):
        for feature in self.data_streams_per_feature:
            _, data_streams = self.data_streams_per_feature[feature]
            data = named_event[0]
            if data in data_streams:
                data_streams[data].emit(named_event)
