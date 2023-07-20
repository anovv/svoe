from queue import Queue

from simulation.events.events import DataEvent


class BaseStrategy:

    def __init__(self, event_queue: Queue):
        self.event_queue = event_queue

    def on_data(self, data_event: DataEvent):
        raise NotImplementedError