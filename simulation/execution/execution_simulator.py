from typing import List, Dict

from simulation.data.data_generator import DataGenerator
from simulation.models.instrument import Instrument
from simulation.models.order import Order, OrderStatus, OrderType, OrderSide
from simulation.models.portfolio import Portfolio


class ExecutionSimulator:

    def __init__(self, portfolio: Portfolio):
        self.orders: List[Order] = []
        self.portfolio: Portfolio = portfolio
        self.cur_mid_prices: Dict[Instrument, float] = {}

    def stage_for_execution(self, orders: List[Order]):
        self.orders.extend(orders)

    def update_state(self, data_event: Dict):
        self.cur_mid_prices = DataGenerator.get_cur_mid_prices(data_event)
        self._execute_staged_orders()

    # here we assume there is always liquidity for execution
    # in future we need to plug current order book snapshot and use it for execution
    def _execute_staged_orders(self):
        for order in self.orders:
            if order.status == OrderStatus.CANCELLED or order.status == OrderStatus.FILLED:
                continue

            # TODO add slippage
            # TODO add latency
            if order.type == OrderType.MARKET:
                # immediate execution
                self._execute_order(order)

            if order.type == OrderType.LIMIT:
                if order.instrument not in self.cur_mid_prices:
                    raise ValueError(f'Instrument {order.instrument} not in cur_mid_prices')
                if order.side == OrderSide.BUY:
                    # execute only if it is below mid price
                    if order.price <= self.cur_mid_prices[order.instrument]:
                        self._execute_order(order)
                else:
                    # execute only if it is above mid price
                    if order.price >= self.cur_mid_prices[order.instrument]:
                        self._execute_order(order)

    def _execute_order(self, order: Order):
        pass







