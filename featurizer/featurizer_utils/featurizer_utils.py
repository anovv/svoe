import heapq
import time
from typing import Dict, List, Tuple

from featurizer.blocks.blocks import BlockRange
from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature


# TODO util this
# TODO we assume no 'holes' here
# TODO use merge_ordered
# TODO this is slow
def merge_blocks(
    blocks: Dict[Feature, BlockRange]
) -> List[Tuple[Feature, Event]]:
    # TODO if only one feature, map directly
    merged = None
    features = list(blocks.keys())
    for i in range(0, len(features)):
        feature = features[i]
        block_range = blocks[feature]
        named_events = []
        for block in block_range:
            t = time.time()
            parsed = feature.feature_definition.parse_events(block)
            print(f'[{feature}] Parsed block in {time.time() - t}s')
            named = []
            for e in parsed:
                named.append((feature, e))
            named_events = list(heapq.merge(named_events, named, key=lambda named_event: named_event[1]['timestamp']))

        if i == 0:
            merged = named_events
        else:
            # TODO explore heapdict
            merged = list(heapq.merge(merged, named_events, key=lambda named_event: named_event[1]['timestamp']))

    return merged