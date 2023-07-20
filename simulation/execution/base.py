from queue import Queue

from simulation.events.events import OrderEvent


class BaseExecutionSimulator:

    def __init__(self, event_queue: Queue):
        self.event_queue = event_queue

    def on_order(self, order_event: OrderEvent):
        raise NotImplementedError