from typing import List
from portion import IntervalDict
from data_catalog.blocks.blocks import BlockMeta, get_interval


# TODO change to List[BlockRangeMeta] when use holes
def identity_grouping(ranges: List[BlockMeta]) -> IntervalDict:
    # groups blocks 1 to 1
    res = IntervalDict()
    # TODO assuming no 'holes' in data
    for meta in ranges:
        res[get_interval(meta)] = [meta]
    return res
