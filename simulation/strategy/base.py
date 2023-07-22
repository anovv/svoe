from queue import Queue
from typing import Dict, List, Optional

from simulation.events.events import DataEvent
from simulation.models.order import Order
from simulation.models.portfolio import Portfolio


class BaseStrategy:

    def __init__(self, portfolio_config: Dict):
        self.portfolio = Portfolio.from_config(portfolio_config)

    def on_data(self, data_event: DataEvent) -> Optional[List[Order]]:
        raise NotImplementedError