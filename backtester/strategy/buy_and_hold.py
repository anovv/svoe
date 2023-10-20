from typing import List, Optional

from backtester.data.data_generator import DataStreamEvent
from backtester.models.order import Order
from backtester.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        raise NotImplementedError