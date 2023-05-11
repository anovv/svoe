from typing import Dict, List, Any
import pandas as pd
from portion import Interval, closed, IntervalDict

from featurizer.sql.data_catalog.models import DataCatalog

BlockMeta = Dict # represents s3 file metadata: name, time range, size, etc.
BlockRangeMeta = List[BlockMeta] # represents metadata of consecutive blocks

Block = pd.DataFrame
BlockRange = List[Block] # represents consecutive blocks

# TODO common consts for start_ts, end_ts, etc


def meta_to_interval(meta: BlockMeta) -> Interval:
    start = float(meta[DataCatalog.start_ts.name])
    end = float(meta[DataCatalog.end_ts.name])
    if start > end:
        raise ValueError('start_ts cannot be greater than end_ts')
    return closed(start, end)


def range_meta_to_interval(range_meta: BlockRangeMeta) -> Interval:
    start = float(range_meta[0][DataCatalog.start_ts.name])
    end = float(range_meta[-1][DataCatalog.end_ts.name])
    if start > end:
        raise ValueError('start_ts cannot be greater than end_ts')
    return closed(start, end)


def interval_to_meta(interval: Interval) -> BlockMeta:
    return {
        DataCatalog.start_ts.name: interval.lower,
        DataCatalog.end_ts.name: interval.upper,
    }


def ranges_to_interval_dict(ranges: List[BlockRangeMeta]) -> IntervalDict:
    res = IntervalDict()
    for range in ranges:
        interval = range_meta_to_interval(range)
        keys = list(res.keys())
        for i in keys:
            if i.overlaps(interval):
                raise ValueError(f'Overlapping intervals: {i} and {interval}')

        res[interval] = range

    return res


def mock_meta(start_ts, end_ts, extra=None) -> BlockMeta:
    res = {
        DataCatalog.start_ts.name: float(start_ts),
        DataCatalog.end_ts.name: float(end_ts)
    }

    if extra:
        res.update(extra)
    return res

def make_ranges(data: List[BlockMeta]) -> List[BlockRangeMeta]:
    # TODO validate ts sorting

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


def identity_grouping(ranges: List[BlockMeta]) -> IntervalDict:
    # groups blocks 1 to 1
    res = IntervalDict()
    for meta in ranges:
        res[meta_to_interval(meta)] = [meta]
    return res


def get_overlaps(key_intervaled_value: Dict[Any, IntervalDict]) -> Dict[Interval, Dict]:
    # TODO add visualization?
    # https://github.com/AlexandreDecan/portion
    # https://stackoverflow.com/questions/40367461/intersection-of-two-lists-of-ranges-in-python
    d = IntervalDict()
    first_key = list(key_intervaled_value.keys())[0]
    for interval, values in key_intervaled_value[first_key].items():
        d[interval] = {first_key: values}  # named_intervaled_values_dict

    # join intervaled_values_dict for each key with first to find all possible intersecting intervals
    # and their corresponding values
    for key, intervaled_values_dict in key_intervaled_value.items():
        if key == first_key:
            continue

        def concat(named_intervaled_values_dict, values):
            # TODO copy.deepcopy?
            res = named_intervaled_values_dict.copy()
            res[key] = values
            return res

        combined = d.combine(intervaled_values_dict, how=concat)  # outer join
        d = combined[d.domain() & intervaled_values_dict.domain()]  # inner join

    # make sure all intervals are closed
    res = {}
    for interval, value in d.items():
        res[closed(interval.lower, interval.upper)] = value
    return res


# TODO test this
def prune_overlaps(overlaps: Dict[Interval, Dict[Any, List]]) -> Dict[Interval, Dict[Any, List]]:
    for interval in overlaps:
        ranges = overlaps[interval]
        for key in ranges:
            range = ranges[key]
            pruned = []
            for meta in range:
                if interval.overlaps(meta_to_interval(meta)):
                    pruned.append(meta)
            if len(pruned) == 0:
                raise ValueError(f'Unable to prune key {key}')
            ranges[key] = pruned
    return overlaps

