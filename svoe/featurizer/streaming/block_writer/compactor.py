from typing import List

import pandas as pd

from svoe.featurizer.data_definitions.data_definition import Event
from svoe.featurizer.features.feature_tree.feature_tree import Feature


class Compactor:
    def __init__(self, config):
        self.config = config

    def compaction_split_indexes(self, feature: Feature, events: List[Event]) -> List[int]:
        raise NotImplementedError

    # not thread safe
    def compact(self, feature: Feature, events: List[Event]) -> List[pd.DataFrame]:
        split_indexes = self.compaction_split_indexes(feature, events)
        if len(split_indexes) == 0:
            return []
        dfs = []
        prev_index = 0
        for split_index in split_indexes:
            to_store = events[prev_index: split_index + 1]
            prev_index = split_index
            # TODO sort by ts
            # TODO make sure all ts in current block are greater then largest ts in prev block
            df = pd.DataFrame(to_store)
            dfs.append(df)

        del events[:split_indexes[-1] + 1]
        return dfs
