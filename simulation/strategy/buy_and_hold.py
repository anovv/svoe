from simulation.events.events import DataEvent, SignalEvent
from simulation.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data(self, data_event: DataEvent):
        signal_data = {
            'exchange': data_event.exchange,
            'instrument_type': data_event.instrument_type,
            'symbol': data_event.symbol,
            'side': 'BUY'
        }
        signal = SignalEvent(
            data_event.timestamp,
            signal_data
        )
        self.event_queue.put(signal)