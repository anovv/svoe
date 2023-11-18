from typing import List, Optional

import pandas as pd

from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature


class Compactor:

    def compaction_split_index(self, feature: Feature, events: List[Event], **kwargs) -> Optional[int]:
        raise NotImplementedError

    # not thread safe
    def compact(self, feature: Feature, events: List[Event], **kwargs) -> Optional[pd.DataFrame]:
        split_index = self.compaction_split_index(feature, events, **kwargs)
        if split_index is None:
            return None
        to_store = events[:split_index + 1]

        # TODO sort by ts
        # TODO make sure all ts in current block are greater then largest ts in prev block

        df = pd.DataFrame(to_store)
        del events[:split_index + 1]
        return df
