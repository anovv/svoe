import sys
import time
from typing import List, Optional, Dict

import pandas as pd

from common.pandas.df_utils import get_size_kb
from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature


class MemoryBasedCompactor:

    def __init__(self):
        self._estimated_num_events_per_block: Dict[Feature, int] = {}
        pass

    def compaction_split_indexes(self, feature: Feature, events: List[Event], **kwargs) -> List[int]:
        in_memory_size_kb = kwargs['in_memory_size_kb']

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
        num_events_per_1kb = 20  # approx num event per 1 kb in terms of pandas df size in-memory
        num_events_per_block = num_events_per_1kb * in_memory_size_kb

        df = pd.DataFrame(events[:num_events_per_block + 1])
        approx_size_kb = get_size_kb(df)

        # proportionally scale num_events
        # TODO finish
        # num_events_per_block = num_events_per_block *


        return num_events_per_block



if __name__ == '__main__':
    events = [{
        'ts1': time.time(),
        'ts2': time.time(),
        'val1': i * 1_000_000,
        'val2': i * 1_000_000,
        'val3': i * 1_000_000,
        'val4': i * 1_000_000,
    } for i in range(2 * 1000 * 1000)]

    df = pd.DataFrame(events)

    print(sys.getsizeof(events)/1024)
    print(sys.getsizeof(df)/1024)
    print(get_size_kb(df))