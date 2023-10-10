from typing import List, Optional

from simulation.data.data_generator import DataStreamEvent
from simulation.models.order import Order
from simulation.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        raise NotImplementedError