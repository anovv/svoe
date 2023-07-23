from queue import Queue
from typing import Dict, Type

from featurizer.config import FeaturizerConfig
from simulation.data.data_generator import DataGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.strategy.base import BaseStrategy


class Loop:

    def __init__(self, featurizer_config: FeaturizerConfig, portfolio_config: Dict, strategy_class: Type[BaseStrategy]):
        self.data_generator = DataGenerator(featurizer_config)
        self.strategy = strategy_class(portfolio_config)
        self.execution_simulator = ExecutionSimulator()
        self.is_running = False

    def set_is_running(self, running):
        self.is_running = running


    # TODO add global clock
    def run(self):
        self.is_running = True
        while self.is_running and not self.data_generator.should_stop():
            data_event = self.data_generator.next()
            orders = self.strategy.on_data(data_event)
            self.execution_simulator.execute(orders)


