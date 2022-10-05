from typing import List, Optional, Any
from streamz import Stream


def sample(upstream: Stream, window: str = '1s') -> Stream:
    def _convert_to_seconds(s):
        seconds_per_unit = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        return int(s[:-1]) * seconds_per_unit[s[-1]]

    def _pass_if_needed(last_ts: List[Optional[float]], event: Any) -> Optional[Any]:
        ts = event.timestamp
        if last_ts[0] is None or ts - last_ts[0] > _convert_to_seconds(window):
            last_ts[0] = ts
            return last_ts, event
        else:
            return last_ts, None

    acc = upstream.accumulate(_pass_if_needed, returns_state=True, start=[None])
    return filter_none(acc)


def filter_none(upstream: Stream):
    return upstream.filter(lambda x: x is not None)


