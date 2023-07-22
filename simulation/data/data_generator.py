from typing import Dict, List

from intervaltree import Interval

from featurizer.blocks.blocks import BlockRangeMeta, Block, BlockRange
from featurizer.calculator.tasks import merge_blocks
from featurizer.config import FeaturizerConfig
from featurizer.features.feature_tree.feature_tree import construct_feature_tree, Feature
from featurizer.storage.featurizer_storage import FeaturizerStorage, data_key
from simulation.events.events import DataEvent


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

        storage = FeaturizerStorage()
        data_deps = set()
        for feature in self.features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=featurizer_config.start_date,
                                                         end_date=featurizer_config.end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps} # Dict[Feature, List[BlockRangeMeta]]
        self.data_ranges = self.load_data_ranges(data_ranges_meta)


    # TODO util this?
    def load_data_ranges(self, data_ranges_meta: Dict[Feature, List[BlockRangeMeta]]) -> Dict[Interval, Dict[Feature, BlockRange]]:
        return {} # TODO


    def next(self) -> DataEvent:
        upstream_per_feature = {f: {} for f in self.features}

        for interval in self.data_ranges:
            data_deps = self.data_ranges[interval]
            merged = merge_blocks(data_deps)

            raise # TODO

    def should_stop(self) -> bool:
        raise # TODO