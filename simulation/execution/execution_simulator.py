import uuid
from typing import List, Dict, Optional, Tuple

from simulation.data.data_generator import DataGenerator
from simulation.models.instrument import Instrument, AssetInstrument
from simulation.models.order import Order, OrderStatus, OrderType, OrderSide
from simulation.models.portfolio import Portfolio
from simulation.models.trade import Trade

COMMISSION = 0.005 # TODO make dynamic

class ExecutionSimulator:

    def __init__(self, portfolio: Portfolio):
        self.orders: List[Order] = []
        self.portfolio: Portfolio = portfolio
        self.cur_mid_prices: Dict[Instrument, float] = {}

    def stage_for_execution(self, orders: List[Order]):
        self.orders.extend(orders)

    def update_state(self, data_event: Dict):
        self.cur_mid_prices = DataGenerator.get_cur_mid_prices(data_event)
        trades = self._execute_staged_orders()
        if len(trades) > 0:
            # TODO report trades to ledger
            pass

        # TODO snapshot portfolio on each trade/update step?

    # here we assume there is always liquidity for execution
    # in future we need to plug current order book snapshot and use it for execution
    def _execute_staged_orders(self) -> List[Trade]:
        res = []
        for order in self.orders:
            if order.status == OrderStatus.CANCELLED or order.status == OrderStatus.FILLED:
                continue

            # TODO add slippage
            # TODO add latency
            # TODO add commission
            if order.type == OrderType.MARKET:
                # immediate execution
                res.append(self._execute_order(order))

            if order.type == OrderType.LIMIT:
                if order.instrument not in self.cur_mid_prices:
                    raise ValueError(f'Instrument {order.instrument} not in cur_mid_prices')
                if order.side == OrderSide.BUY:
                    # execute only if it is below mid price
                    if order.price <= self.cur_mid_prices[order.instrument]:
                        res.append(self._execute_order(order))
                else:
                    # execute only if it is above mid price
                    if order.price >= self.cur_mid_prices[order.instrument]:
                        res.append(self._execute_order(order))

        return res

    def _execute_order(self, order: Order) -> Trade:
        price = self.cur_mid_prices[order.instrument]

        base_asset_instr, quote_asset_instr = order.instrument.to_asset_instruments()

        trade_id = str(uuid.uuid4())

        if order.side == OrderSide.BUY:
            # quote -> base
            asset_instr_from = quote_asset_instr
            asset_instr_to = base_asset_instr
            wallet_from = self.portfolio.get_wallet(asset_instr_from)
            wallet_to = self.portfolio.get_wallet(asset_instr_to)

            # we assume qty  was already locked, so no deduction here
            quote_qty = wallet_from.unlock(order.order_id)
            # TODO slippage
            commission = quote_qty * price * COMMISSION
            base_qty = quote_qty * price - commission
            wallet_to.deposit(base_qty)
            trade = Trade(
                trade_id=trade_id,
                order_id=order.order_id,
                instrument=order.instrument,
                side=order.side,
                trade_type=order.type,
                quantity=base_qty,
                price=price,
                commission=commission
            )
        else:
            # base -> quote
            asset_instr_from = base_asset_instr
            asset_instr_to = quote_asset_instr
            wallet_from = self.portfolio.get_wallet(asset_instr_from)
            wallet_to = self.portfolio.get_wallet(asset_instr_to)

            # we assume qty  was already locked, so no deduction here
            base_qty = wallet_from.unlock(order.order_id)
            # TODO  slippage
            commission = (base_qty / price) * COMMISSION
            quote_qty = (base_qty / price) - commission
            wallet_to.deposit(quote_qty)
            trade = Trade(
                trade_id=trade_id,
                order_id=order.order_id,
                instrument=order.instrument,
                side=order.side,
                trade_type=order.type,
                quantity=base_qty,
                price=price,
                commission=commission
            )

        order.status = OrderStatus.FILLED # TODO is it by ref? does it update self.orders?
        return trade
