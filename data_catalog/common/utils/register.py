import time
from enum import Enum
from typing import List, Dict, Optional
from functools import wraps

import ray


class EventType(Enum):
    SCHEDULED = 'scheduled'
    STARTED = 'started'
    FINISHED = 'finished'


EVENT_NAMES = []
TASK_NAMES = []


def report_stats_decor(event_types: List[EventType]):
    def decorate(task):
        # register event names and task names for stats dashboards
        for event_type in event_types:
            EVENT_NAMES.append(get_event_name(task.__name__, event_type))

        TASK_NAMES.append(task.__name__)

        @wraps(task)
        def wrapper(*args, **kwargs):
            task_id = kwargs['task_id']
            stats = kwargs['stats']
            extra = kwargs.get('stats_extra', {})
            task_name = task.__name__
            if EventType.STARTED in event_types:
                _send_events_to_stats(stats, [task_id], task_name, EventType.STARTED, [extra])
            start = time.time()
            res = task(*args, **kwargs)
            latency = time.time() - start
            extra['latency'] = latency
            if EventType.FINISHED in event_types:
                _send_events_to_stats(stats, [task_id], task_name, EventType.FINISHED, [extra])
            return res

        return wrapper
    return decorate

@ray.remote
def send_events_to_stats(stats: 'Stats', task_ids: List[str], task_name: str, event_type: EventType, extras: List[Optional[Dict]]):
    _send_events_to_stats(stats, task_ids, task_name, event_type, extras)


def _send_events_to_stats(stats: 'Stats', task_ids: List[str], task_name: str, event_type: EventType, extras: List[Optional[Dict]]):
    if len(task_ids) != len(extras):
        raise ValueError('Each task should have corresponding extra')

    events = [{
        'task_id': task_id,
        'event_name': get_event_name(task_name, event_type),
        'timestamp': time.time()
    } for task_id in task_ids]

    for i in range(len(extras)):
        events[i].update(extras[i])
    stats.send_events.remote(task_name, events)


def get_event_name(task_name: str, event_type: EventType) -> str:
    return task_name + '_' + event_type.value


def ray_task_name(task) -> str:
    d = task.__dict__
    if '_func' in d:
        return d['_func'].__name__

    if '_function' in d:
        return d['_function'].__name__

    raise ValueError(f'Unable to parse underlying function name from ray task: {d}')
