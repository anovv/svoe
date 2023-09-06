import pandas as pd

from simulation.clock import Clock
from simulation.data.data_generator import DataStreamGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy


class Loop:

    def __init__(
            self,
            clock: Clock,
            data_generator: DataStreamGenerator,
            portfolio: Portfolio,
            strategy: BaseStrategy,
            execution_simulator: ExecutionSimulator):
        self.clock = clock
        self.data_generator = data_generator
        self.portfolio = portfolio
        self.strategy = strategy
        self.execution_simulator = execution_simulator
        self.is_running = False

    def set_is_running(self, running):
        self.is_running = running

    def run(self):
        self.is_running = True
        while self.is_running and self.data_generator.has_next():
            data_event = self.data_generator.next()
            if data_event is not None:
                ts = data_event.timestamp
                self.clock.set(ts)
                orders = self.strategy.on_data(data_event)
                if orders is not None and len(orders) > 0:
                    self.execution_simulator.stage_for_execution(orders)
                self.execution_simulator.update_state()
        self.is_running = False
        # print(self.execution_simulator.balances_df())
        # df = pd.merge(self.execution_simulator.prices_df(), self.execution_simulator.balances_df(), how='outer', on='timestamp')

        prices = self.execution_simulator.prices_df()
        prices = prices.drop_duplicates()
        print(prices)
        print(self.execution_simulator.balances_df())

        df = pd.merge(prices, self.execution_simulator.balances_df(), on='timestamp')
        # print(df)

        trades = self.execution_simulator.trades_df()
        trades = trades[trades.symbol == 'BTC-USDT']
        # print(trades)



