import math
from datetime import datetime

import pytz


def convert_str_to_seconds(s: str) -> int:
    seconds_per_unit = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    return int(s[:-1]) * seconds_per_unit[s[-1]]


def date_str_from_ts(ts) -> str:
    dt_obj = datetime.fromtimestamp(float(ts), tz=pytz.utc)
    return f'{dt_obj.year}-{dt_obj:%m}-{dt_obj:%d}'
