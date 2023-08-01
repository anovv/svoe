from queue import Queue
from typing import Dict, Type

from featurizer.config import FeaturizerConfig
from simulation.clock import Clock
from simulation.data.data_generator import DataGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy


class Loop:

    def __init__(
            self,
            featurizer_config: FeaturizerConfig,
            portfolio_config: Dict,
            strategy_class: Type[BaseStrategy],
            predictor_config: Dict):
        self.clock = Clock(-1)
        self.data_generator = DataGenerator(featurizer_config) # TODO parametrize DataGenerator class
        self.portfolio = Portfolio.from_config(portfolio_config)
        self.strategy = strategy_class(self.portfolio, predictor_config)
        self.execution_simulator = ExecutionSimulator(self.clock, self.portfolio, self.data_generator)
        self.is_running = False

    def set_is_running(self, running):
        self.is_running = running


    # TODO add global clock
    def run(self):
        self.is_running = True
        while self.is_running and self.data_generator.has_next():
            data_event = self.data_generator.next()
            if data_event is not None:
                ts = data_event['timestamp'] # TODO
                self.clock.set(ts)
                orders = self.strategy.on_data(data_event)
                if orders is not None and len(orders) > 0:
                    self.execution_simulator.stage_for_execution(orders)
                self.execution_simulator.update_state()



