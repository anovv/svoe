import time
from enum import Enum
from typing import List, Dict
from functools import wraps

from data_catalog.indexer.actors.stats import Stats


class EventType(Enum):
    SCHEDULED = 'scheduled'
    STARTED = 'donwloaded'
    FINISHED = 'finished'


EVENT_NAMES = []
TASK_NAMES = []


def report_stats_decor(event_types: List[EventType]):
    def decorate(task):
        # register event names and task names for stats dashboards
        for event_type in event_types:
            EVENT_NAMES.append(_event_name(task.__name__, event_type))

        TASK_NAMES.append(task.__name__)

        @wraps(task)
        def wrapper(*args, **kwargs):
            task_id = kwargs['task_id']
            stats = kwargs['stats']
            extra = kwargs['extra']
            task_name = task.__name__

            # TODO event_type -> event_name
            event = {
                'task_id': task_id,
                'event_type': _event_name(task_name, EventType.STARTED),
                'timestamp': time.time()
            }
            if extra is not None and 'size_kb' in extra:
                event['size_kb'] = extra['size_kb']
            if EventType.STARTED in event_types:
                stats.event.remote(task_name, event)
            res = task(*args, **kwargs)
            event['event_type'] = _event_name(task_name, EventType.FINISHED)
            now = time.time()
            event['latency'] = now - event['timestamp']
            event['timestamp'] = now
            if EventType.FINISHED in event_types:
                stats.event.remote(task_name, event)

            return res

        return wrapper
    return decorate


def _event_name(task_name: str, event_type: EventType) -> str:
    return task_name + '_' + event_type.value
