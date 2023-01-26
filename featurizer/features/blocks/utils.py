from typing import List, Dict
from featurizer.features.blocks.blocks import BlockMeta, get_interval


# TODO change to List[BlockRangeMeta] when use holes
def identity_grouping(ranges: List[BlockMeta]) -> Dict:
    # groups blocks 1 to 1
    res = {}
    # TODO assuming no 'holes' in data
    for meta in ranges:
        res[get_interval(meta)] = [meta]
    return res
