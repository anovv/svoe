from typing import Dict, List, Tuple

from intervaltree import Interval

from featurizer.blocks.blocks import BlockRangeMeta, Block, BlockRange
from featurizer.calculator.tasks import merge_blocks
from featurizer.config import FeaturizerConfig
from featurizer.features.feature_tree.feature_tree import construct_feature_tree, Feature, construct_stream_tree
from featurizer.storage.featurizer_storage import FeaturizerStorage, data_key
from simulation.events.events import DataEvent
import featurizer.data_definitions.data_definition as f


class DataGenerator:

    def __init__(self, featurizer_config: FeaturizerConfig):
        # TODO this logic is duplicated in featurizer/runner.py, util it?
        self.features = []
        for feature_config in featurizer_config.feature_configs:
            self.features.append(construct_feature_tree(
                feature_config.feature_definition,
                feature_config.data_params,
                feature_config.feature_params
            ))

        # build data streams trees
        self.data_streams_per_feature = {}
        for f in self.features:
            out, data_streams = construct_stream_tree(f)
            self.data_streams_per_feature[f] = out, data_streams

        storage = FeaturizerStorage()
        data_deps = set()
        for feature in self.features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=featurizer_config.start_date,
                                                         end_date=featurizer_config.end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps} # Dict[Feature, List[BlockRangeMeta]]
        data_ranges = self.load_data_ranges(data_ranges_meta)
        self.input_data_events = self.merge_data_ranges(data_ranges)
        self.cur_interval_id = 0
        self.cur_input_event_index = 0


    # TODO util this?
    def load_data_ranges(self, data_ranges_meta: Dict[Feature, List[BlockRangeMeta]]) -> Dict[Interval, Dict[Feature, BlockRange]]:
        return {} # TODO

    def merge_data_ranges(self, data_ranges: Dict[Interval, Dict[Feature, BlockRange]]) -> Dict[Interval, List[Tuple[Feature, f.Event]]]:
        return {i: merge_blocks(b) for i, b in data_ranges}

    def next(self) -> DataEvent:
        # move interval if necessary
        if self.cur_interval_id >= len(self.input_data_events.keys()):
            raise ValueError('DataGenerator out of bounds')
        interval = list(self.input_data_events.keys())[self.cur_interval_id]
        input_events = self.input_data_events[interval]
        if self.cur_input_event_index >= len(input_events):
            self.cur_interval_id += 1
            self.cur_input_event_index = 0
            interval = list(self.input_data_events.keys())[self.cur_interval_id]
            input_events = self.input_data_events[interval]

        data, input_event = input_events[self.cur_input_event_index] # Tuple[Feature, f.Event]
        self.cur_input_event_index += 1

        # TODO loop through self.data_streams_per_feature and emit new event for each data key, record emitted state, create feature snapshot

    def should_stop(self) -> bool:
        return self.cur_interval_id >= len(self.input_data_events.keys())


