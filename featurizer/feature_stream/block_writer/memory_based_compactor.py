import sys
import time
from typing import List, Optional

import pandas as pd

from common.pandas.df_utils import get_size_kb
from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature


class MemoryBasedCompactor:

    def __init__(self):
        pass

    def compaction_split_index(self, feature: Feature, events: List[Event], **kwargs) -> Optional[int]:
        in_memory_size = kwargs['in_memory_size']
        num_events_chunk_size = 20000 # approx num event per 1 mb in terms of pandas df size
        # TODO binary search

        return None


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