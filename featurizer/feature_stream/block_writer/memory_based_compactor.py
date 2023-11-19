import sys
import time
from typing import List, Dict, Optional

import pandas as pd

from common.pandas.df_utils import get_size_kb, get_size_bytes
from featurizer.data_definitions.data_definition import Event
from featurizer.feature_stream.block_writer.compactor import Compactor
from featurizer.features.feature_tree.feature_tree import Feature


class MemoryBasedCompactor(Compactor):

    def __init__(self, config):
        super().__init__(config)
        self._estimated_num_events_per_block: Dict[Feature, int] = {}

    def compaction_split_indexes(self, feature: Feature, events: List[Event],) -> List[int]:
        in_memory_size_kb = self.config['in_memory_size_kb']

        if feature in self._estimated_num_events_per_block:
            num_events_per_block = self._estimated_num_events_per_block[feature]
        else:
            num_events_per_block = self._estimate_num_events(events, in_memory_size_kb)
            self._estimated_num_events_per_block[feature] = num_events_per_block

        res = []
        cur_index = num_events_per_block - 1
        length = len(events)
        while cur_index <= length:
            res.append(cur_index)
            cur_index += num_events_per_block

        return res

    def _estimate_num_events(self, events: List[Event], in_memory_size_kb: int) -> int:
        num_events_per_1kb = 20  # approx num events per 1 kb in terms of pandas df size in-memory
        num_events_per_block = num_events_per_1kb * in_memory_size_kb

        df = pd.DataFrame(events[:num_events_per_block + 1])
        approx_size_bytes = get_size_bytes(df)
        print(approx_size_bytes)
        # if approx_size_kb == 0:
        #     return None

        # proportionally scale num_events
        num_events_per_block = int(num_events_per_block * in_memory_size_kb * 1024 / approx_size_bytes )

        print(num_events_per_block)
        return num_events_per_block
