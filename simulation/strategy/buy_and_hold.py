from simulation.events.events import DataEvent
from simulation.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data(self, data_event: DataEvent):
        raise