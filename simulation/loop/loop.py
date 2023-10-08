from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional

from ray.serve.deployment import Deployment

from simulation.clock import Clock
from simulation.data.data_generator import DataStreamGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.inference.inference import start_serve_predictor_deployment
from simulation.models.instrument import Instrument
from simulation.models.portfolio import Portfolio, PortfolioBalanceRecord
from simulation.models.trade import Trade
from simulation.strategy.base import BaseStrategy


@dataclass
class LoopRunResult:
    executed_trades: Dict[Instrument, List[Trade]]
    portfolio_balances: List[PortfolioBalanceRecord]
    sampled_prices: Dict[Instrument, List[Tuple[float, float]]]
    inference_results: List[Tuple[Any, float]]


class Loop:

    def __init__(
        self,
        clock: Clock,
        data_generator: DataStreamGenerator,
        portfolio: Portfolio,
        strategy: BaseStrategy,
        execution_simulator: ExecutionSimulator
    ):
        self.clock = clock
        self.data_generator = data_generator
        self.portfolio = portfolio
        self.strategy = strategy
        self.execution_simulator = execution_simulator
        self.predictor_deployment: Optional[Deployment] = None
        self.is_running = False

    def stop(self):
        self.is_running = False
        if self.strategy.inference_loop is not None:
            self.strategy.inference_loop.stop()
        if self.predictor_deployment is not None:
            self.predictor_deployment.delete()

    def run(self):
        self.is_running = True

        if self.strategy.inference_config is not None:
            self.predictor_deployment = start_serve_predictor_deployment(
                self.strategy.inference_config
            )
            self.strategy.inference_loop.start()
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
        self.strategy.inference_loop.stop()

        inference_results = []
        if self.strategy.inference_loop is not None:
            inference_results = self.strategy.inference_loop.inference_results
        return LoopRunResult(
            executed_trades=self.execution_simulator.executed_trades,
            portfolio_balances=self.execution_simulator.get_portfolio_balances(),
            sampled_prices=self.data_generator.get_sampled_mid_prices(),
            inference_results=inference_results
        )
