import copy
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import pandas as pd

from simulation.clock import Clock
from simulation.data.data_generator import DataGenerator
from simulation.models.instrument import Instrument, AssetInstrument
from simulation.models.order import Order, OrderStatus, OrderType, OrderSide
from simulation.models.portfolio import Portfolio
from simulation.models.trade import Trade

COMMISSION = 0.005 # TODO make dynamic


class ExecutionSimulator:
    @dataclass
    class _State:
        portfolio: Portfolio
        mid_prices: Dict[Instrument, float]
        timestamp: float
        total_balance: float

    def __init__(self, clock: Clock, portfolio: Portfolio, data_generator: DataGenerator):
        self.clock = clock
        self.orders: List[Order] = []
        self.portfolio: Portfolio = portfolio
        self.data_generator = data_generator
        # self.cur_mid_prices: Dict[Instrument, float] = {}
        self.state_snapshots: List[ExecutionSimulator._State] = []
        self.executed_trades: List[Tuple[float, Trade]] = []

    def stage_for_execution(self, orders: List[Order]):
        if len(orders) > 0:
            self.orders.extend(orders)
            self._record_state_snapshot()

    def update_state(self):
        # self.cur_mid_prices = self.data_generator.get_cur_mid_prices()
        trades = self._execute_staged_orders()
        if len(trades) > 0:
            ts = self.clock.now
            trades_with_ts = list(map(lambda t: (ts, t), trades))
            self.executed_trades.extend(trades_with_ts)
            self._record_state_snapshot()

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

            mid_prices = self.data_generator.get_cur_mid_prices()
            if order.type == OrderType.LIMIT:
                if order.instrument not in mid_prices:
                    raise ValueError(f'Instrument {order.instrument} not in mid_prices')
                if order.side == OrderSide.BUY:
                    # execute only if it is below mid price
                    if order.price <= mid_prices[order.instrument]:
                        res.append(self._execute_order(order))
                else:
                    # execute only if it is above mid price
                    if order.price >= mid_prices[order.instrument]:
                        res.append(self._execute_order(order))

        return res

    def _execute_order(self, order: Order) -> Trade:
        mid_prices = self.data_generator.get_cur_mid_prices()
        price = mid_prices[order.instrument]

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
            commission = (quote_qty / price) * COMMISSION
            base_qty = (quote_qty / price) - commission
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
            commission = (base_qty * price) * COMMISSION
            quote_qty = (base_qty * price) - commission
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

    def _record_state_snapshot(self):
        quote_wallet = self.portfolio.get_wallet(self.portfolio.quote)
        total_balance = quote_wallet.total_balance()

        mid_prices = self.data_generator.get_cur_mid_prices()
        for wallet in self.portfolio.wallets:
            asset_instrument = wallet.asset_instrument
            if asset_instrument == self.portfolio.quote:
                continue
            instrument = Instrument.from_asset_instruments(base=asset_instrument, quote=self.portfolio.quote)
            if instrument not in mid_prices:
                raise ValueError(f'Can not find mid_price for {instrument}')
            mid_price = mid_prices[instrument]
            wallet = self.portfolio.get_wallet(asset_instrument)
            total_balance += (wallet.total_balance() * mid_price)

        snapshot = ExecutionSimulator._State(
            portfolio=copy.deepcopy(self.portfolio),
            # TODO this records different mid_price for same ts, why?
            mid_prices=copy.deepcopy(mid_prices),
            timestamp=self.clock.now,
            total_balance=total_balance
        )
        self.state_snapshots.append(snapshot)

    def balances_df(self) -> pd.DataFrame:
        res = pd.DataFrame()
        for s in self.state_snapshots:
            record = {
                'timestamp': s.timestamp
            }
            for wallet in s.portfolio.wallets:
                record[wallet.asset_instrument.asset + '_free'] = wallet.free_balance()
                record[wallet.asset_instrument.asset + '_locked'] = wallet.locked_balance()
            record['total'] = s.total_balance
            res = res.append(record, ignore_index=True)
        return res

    # TODO this should be on data_generator
    def prices_df(self) -> pd.DataFrame:
        res = pd.DataFrame()
        for s in self.state_snapshots:
            record = {
                'timestamp': s.timestamp
            }
            for inst in s.mid_prices:
                record[inst.symbol] = s.mid_prices[inst]
            res = res.append(record, ignore_index=True)
        return res

    def trades_df(self) -> pd.DataFrame:
        raise NotImplementedError

