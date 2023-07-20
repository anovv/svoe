from simulation.events.events import OrderEvent, FillEvent
from simulation.execution.base import BaseExecutionSimulator


class DefaultExecutionSimulator(BaseExecutionSimulator):

    # instantly generates fill event
    def on_order(self, order_event: OrderEvent):
        fill = FillEvent(
            order_event.timestamp,
            order_event.instrument_type,
            order_event.symbol,
            order_event.order_type,
            order_event.price,
            order_event.quantity,
            order_event.side
        )
        self.event_queue.put(fill)

