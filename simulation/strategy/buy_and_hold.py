from typing import List, Dict, Optional

from simulation.models.order import Order
from simulation.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data_udf(self, data_event: Dict) -> Optional[List[Order]]:
        raise NotImplementedError