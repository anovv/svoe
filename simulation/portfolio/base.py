from queue import Queue

from simulation.events.events import FillEvent, SignalEvent


class BasePortfolio:

    def __init__(self, event_queue: Queue):
        self.event_queue = event_queue

    def on_fill(self, fill_event: FillEvent):
        raise NotImplementedError

    def on_signal(self, signal_event: SignalEvent):
        raise NotImplementedError
