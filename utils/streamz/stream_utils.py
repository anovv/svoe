from typing import List, Optional, Any, Callable, Deque
from streamz import Stream
from utils.time.utils import convert_str_to_seconds
from collections import deque


def throttle(upstream: Stream, window: str = '1s') -> Stream:
    # List represents mutable state with 1 element
    def _pass_if_needed(last_ts: List[Optional[float]], event: Any) -> Optional[Any]:
        ts = event['timestamp']
        if last_ts[0] is None or ts - last_ts[0] > convert_str_to_seconds(window):
            last_ts[0] = ts
            return last_ts, event
        else:
            return last_ts, None

    # init state with [None]
    acc = upstream.accumulate(_pass_if_needed, returns_state=True, start=[None])
    return filter_none(acc)


def filter_none(upstream: Stream) -> Stream:
    return upstream.filter(lambda x: x is not None)


def lookback_apply(upstream: Stream, window: str, apply: Callable) -> Stream:
    def _deque_and_apply(events_deque: Deque, event: Any) -> Any:
        ts = event['timestamp']
        events_deque.append(event)
        first_ts = events_deque[0]['timestamp']
        if ts - first_ts > convert_str_to_seconds(window):
            events_deque.popleft()
        return events_deque, apply(events_deque)

    return upstream.accumulate(_deque_and_apply, returns_state=True, start=deque())



