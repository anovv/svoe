from typing import List, Dict, Optional

from simulation.models.order import Order
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy


class BuyLowSellHighStrategy(BaseStrategy):

    def __init__(self, portfolio: Portfolio, predictor_config: Dict):
        super(BuyLowSellHighStrategy, self).__init__(portfolio, predictor_config)
        self.local_min = None
        self.local_max = None

        self.buy_signal_thresh = 0.1
        self.sell_signal_thresh = 0.1

        self.three_vals = []

        self.is_buying = True

    def on_data_udf(self, data_event: Dict) -> Optional[List[Order]]:
        mid_price = data_event['mid_price']
        self.three_vals.append(mid_price)
        if len(self.three_vals) > 3:
            self.three_vals.pop(0)

        if self._is_local_min():
            self.local_min = self.three_vals[1]

        if self._is_local_max():
            self.local_max = self.three_vals[1]

        if self.is_buying:
            if self.local_max is not None and self.local_max - mid_price > self.buy_signal_thresh * mid_price:
                return self._buy()
        else:
            if self.local_min is not None and mid_price - self.local_min > self.sell_signal_thresh * mid_price:
                return self._sell()

    def _buy(self) -> List[Order]:
        return [] # TODO

    def _sell(self) -> List[Order]:
        return [] # TODO

    def _is_local_min(self) -> bool:
        return self.three_vals[0] > self.three_vals[1] and self.three_vals[2] > self.three_vals[1]

    def _is_local_max(self) -> bool:
        return self.three_vals[0] < self.three_vals[1] and self.three_vals[2] < self.three_vals[1]
