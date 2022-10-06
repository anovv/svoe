from typing import List, Optional, Any
from streamz import Stream
from featurizer.features.utils import convert_str_to_seconds


def throttle(upstream: Stream, window: str = '1s') -> Stream:
    def _pass_if_needed(last_ts: List[Optional[float]], event: Any) -> Optional[Any]:
        ts = event.timestamp
        if last_ts[0] is None or ts - last_ts[0] > convert_str_to_seconds(window):
            last_ts[0] = ts
            return last_ts, event
        else:
            return last_ts, None

    acc = upstream.accumulate(_pass_if_needed, returns_state=True, start=[None])
    return filter_none(acc)


def filter_none(upstream: Stream):
    return upstream.filter(lambda x: x is not None)


