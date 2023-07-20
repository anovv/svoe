from queue import Queue
from typing import Dict, Type

from simulation.data.data_generator import DataGenerator
from simulation.events.events import DataEvent, SignalEvent, OrderEvent, FillEvent
from simulation.execution.default_execution_simulator import DefaultExecutionSimulator
from simulation.portfolio.default_portfolio import DefaultPortfolio
from simulation.strategy.base import BaseStrategy


class Loop:

    def __init__(self, data_config: Dict, strategy_class: Type[BaseStrategy]):
        self.event_queue = Queue()
        self.data_generator = DataGenerator(data_config)
        self.strategy = strategy_class(self.event_queue)
        self.portfolio = DefaultPortfolio(self.event_queue)
        self.execution_simulator = DefaultExecutionSimulator(self.event_queue)
        self.is_running = False

    def set_is_running(self, running):
        self.is_running = running

    def run(self):
        self.is_running = True
        while self.is_running and not self.data_generator.should_stop():
            data_event = self.data_generator.next()
            self.event_queue.put(data_event)
            while self.is_running:
                try:
                    event = self.event_queue.get(block=True)
                except Queue.Empty:
                    break

                if isinstance(event, DataEvent):
                    self.strategy.on_data(event)
                    # portfolio.update_timeindex(event)
                elif isinstance(event, SignalEvent):
                    self.portfolio.on_signal(event)
                elif isinstance(event, OrderEvent):
                    self.execution_simulator.on_order(event)
                elif isinstance(event, FillEvent):
                    self.portfolio.on_fill(event)

