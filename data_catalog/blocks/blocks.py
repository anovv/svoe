from typing import Dict, List
import pandas as pd
from portion import Interval, closed

from data_catalog.common.utils.sql.models import DataCatalog

BlockMeta = Dict # represents s3 file metadata: name, time range, size, etc.
BlockRangeMeta = List[BlockMeta] # represents metadata of consecutive blocks

Block = pd.DataFrame
BlockRange = List[Block] # represents consecutive blocks


def get_interval(meta: BlockMeta) -> Interval:
    start = meta[DataCatalog.start_ts.name]
    end = meta[DataCatalog.end_ts.name]
    if start > end:
        raise ValueError('start_ts cannot be greater than end_ts')
    return closed(meta[DataCatalog.start_ts.name], meta[DataCatalog.end_ts.name])


def make_ranges(data: List[BlockMeta]) -> List[BlockRangeMeta]:
    # if consecuitive files differ no more than this, they are in the same range
    # TODO should this be const per data_type?
    SAME_RANGE_DIFF_S = 1
    ranges = []
    cur_range = []
    for i in range(len(data)):
        cur_range.append(data[i])
        if i < len(data) - 1 and float(data[i + 1][DataCatalog.start_ts.name]) - float(data[i][DataCatalog.end_ts.name]) > SAME_RANGE_DIFF_S:
            ranges.append(cur_range)
            cur_range = []

    if len(cur_range) != 0:
        ranges.append(cur_range)

    return ranges