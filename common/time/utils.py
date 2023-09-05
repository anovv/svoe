import math
from datetime import datetime
from typing import Optional, List, Tuple

import pytz


def convert_str_to_seconds(s: str) -> float:
    if 'ms' in s:
        # millis special case
        return int(s[:-2]) * 0.001
    seconds_per_unit = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    return int(s[:-1]) * seconds_per_unit[s[-1]]


def date_str_from_ts(ts) -> str:
    dt_obj = datetime.fromtimestamp(float(ts), tz=pytz.utc)
    return f'{dt_obj.year}-{dt_obj:%m}-{dt_obj:%d}'


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


def split_date_range(start_date: str, end_date: str) -> List[Tuple[str, str]]:
    raise NotImplementedError

