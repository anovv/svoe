import math
from datetime import datetime
from typing import Optional, List, Tuple

import ciso8601
import pytz
from portion import Interval, closed

SECONDS_IN_DAY = 24 * 60 * 60


def convert_str_to_seconds(s: str) -> float:
    if 'ms' in s:
        # millis special case
        return int(s[:-2]) * 0.001
    seconds_per_unit = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    return int(s[:-1]) * seconds_per_unit[s[-1]]


def day_str_from_ts(ts) -> str:
    dt_obj = datetime.fromtimestamp(float(ts), tz=pytz.utc)
    return f'{dt_obj.year}-{dt_obj:%m}-{dt_obj:%d}'


def date_str_to_ts(date: str) -> float:
    return ciso8601.parse_datetime(date).timestamp()


def ts_to_str_date(ts: float) -> str:
    dt_obj = datetime.fromtimestamp(float(ts), tz=pytz.utc)
    return str(dt_obj)


def date_str_to_day_str(date: str) -> str:
    ts = date_str_to_ts(date)
    return day_str_from_ts(ts)


# divides time into equal buckets starting from 00:00:00:00 UTC based on window_s and gets bucket for given ts
def get_sampling_bucket_ts(timestamp: float, bucket: str, return_bucket_start: Optional[bool] = True) -> float:
    bucket_s = convert_str_to_seconds(bucket)
    if bucket_s > 24 * 60 * 60 or bucket_s < 0.001:
        raise ValueError(f'window_s must be between 1ms and 24h')

    dt = datetime.fromtimestamp(timestamp)
    # for idempotency, we assume 00-00:00.00 of the current day as a starting point for splitting data into blocks
    start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    start_ts = start_dt.timestamp()
    num_buckets = int((timestamp - start_ts)/bucket_s)
    bucket_start_ts = start_ts + num_buckets * bucket_s
    return bucket_start_ts if return_bucket_start else bucket_start_ts + bucket_s


def split_time_range_between_ts(start_ts: float, end_ts: float, num_splits: int, diff_between: float) -> List[Interval]:
    if num_splits == 1:
        return [closed(start_ts, end_ts)]
    split_size = int((end_ts - start_ts) / num_splits)
    intervals = []
    cur_start_ts = start_ts
    cur_end_ts = start_ts + split_size
    while cur_start_ts < end_ts:
        if cur_end_ts <= end_ts:
            intervals.append(closed(cur_start_ts, cur_end_ts))
        else:
            intervals.append(closed(cur_start_ts, end_ts))
        cur_start_ts = cur_end_ts + diff_between
        cur_end_ts = cur_start_ts + split_size

    return intervals


def round_float(f: float) -> float:
    return round(f, 3)
