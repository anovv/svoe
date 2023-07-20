from simulation.events.events import FillEvent, SignalEvent
from simulation.portfolio.base import BasePortfolio


class DefaultPortfolio(BasePortfolio):

    def on_fill(self, fill_event: FillEvent):
        raise

    def on_signal(self, signal_event: SignalEvent):
        raise