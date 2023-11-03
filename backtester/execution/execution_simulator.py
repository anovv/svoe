import copy
import uuid
from dataclasses import dataclass
from typing import List, Dict
from backtester.clock import Clock
from backtester.models.instrument import Instrument, AssetInstrument
from backtester.models.order import Order, OrderStatus, OrderType, OrderSide
from backtester.models.portfolio import Portfolio, PortfolioBalanceRecord
from backtester.models.trade import Trade
from featurizer.feature_stream.feature_stream_generator import FeatureStreamGenerator

COMMISSION = 0.005 # TODO make dynamic


# TODO where does this belong?


class ExecutionSimulator:
    @dataclass
    class _State:
        portfolio: Portfolio
        mid_prices: Dict[Instrument, float]
        timestamp: float
        total_balance: float

    def __init__(self, clock: Clock, portfolio: Portfolio, feature_generator: FeatureStreamGenerator):
        self.clock = clock
        self.orders: List[Order] = []
        self.portfolio: Portfolio = portfolio
        self.feature_generator = feature_generator
        self.state_snapshots: List[ExecutionSimulator._State] = []
        self.executed_trades: Dict[Instrument, List[Trade]] = {}

    def stage_for_execution(self, orders: List[Order]):
        if len(orders) > 0:
            self.orders.extend(orders)
            self._record_state_snapshot()

    def update_state(self):
        trades = self._execute_staged_orders()
        if len(trades) > 0:
            for trade in trades:
                if trade.instrument in self.executed_trades:
                    self.executed_trades[trade.instrument].append(trade)
                else:
                    self.executed_trades[trade.instrument] = [trade]

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

            mid_prices = self.feature_generator.get_cur_mid_prices()
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
        mid_prices = self.feature_generator.get_cur_mid_prices()
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
                timestamp=self.clock.now,
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
            # TODO slippage
            commission = (base_qty * price) * COMMISSION
            quote_qty = (base_qty * price) - commission
            wallet_to.deposit(quote_qty)
            trade = Trade(
                trade_id=trade_id,
                order_id=order.order_id,
                timestamp=self.clock.now,
                instrument=order.instrument,
                side=order.side,
                trade_type=order.type,
                quantity=base_qty,
                price=price,
                commission=commission
            )

        order.status = OrderStatus.FILLED
        return trade

    def _record_state_snapshot(self):
        quote_wallet = self.portfolio.get_wallet(self.portfolio.quote)
        total_balance = quote_wallet.total_balance()

        mid_prices = self.feature_generator.get_cur_mid_prices()
        for wallet in self.portfolio.wallets:
            asset_instrument = wallet.asset_instrument
            if asset_instrument == self.portfolio.quote:
                continue
            instrument = Instrument.from_asset_instruments(base=asset_instrument, quote=self.portfolio.quote)
            if instrument not in mid_prices:
                # TODO why?
                # raise ValueError(f'Can not find mid_price for {instrument}, prices: {mid_prices}')
                continue
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

    def get_portfolio_balances(self) -> List[PortfolioBalanceRecord]:
        records = []
        for s in self.state_snapshots:
            record = PortfolioBalanceRecord(
                timestamp=s.timestamp,
                total=s.total_balance,
                per_wallet={}
            )
            for wallet in s.portfolio.wallets:
                record.per_wallet[wallet.asset_instrument] = wallet.get_free_and_locked_balance()
            records.append(record)
        return records

    def get_executed_trades(self) -> Dict[Instrument, List[Trade]]:
        return self.executed_trades
