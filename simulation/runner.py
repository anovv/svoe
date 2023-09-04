from typing import List, Any

import ray

from simulation.actors.simulation_worker_actor import SimulationWorkerActor
from simulation.clock import Clock
from simulation.data.data_generator import DataGenerator
from simulation.data.feature_stream.feature_stream_generator import FeatureStreamGenerator
from simulation.data.sine.sine_data_generator import SineDataGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.loop.loop import Loop
from simulation.models.instrument import Instrument
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy
from simulation.strategy.buy_low_sell_high import BuyLowSellHighStrategy


class SimulationRunner:

    def __init__(self, generators: List[DataGenerator], portfolio: Portfolio, strategy: BaseStrategy, execution_simulator: ExecutionSimulator):
        self.generators = generators
        self.portfolio = portfolio
        self.strategy = strategy
        self.execution_simulator = execution_simulator
        # TODO config?
        pass

    def run_single(self):
        loop = Loop(
            clock=clock,
            data_generator=self.generators[0],
            portfolio=self.portfolio,
            strategy=self.strategy,
            execution_simulator=self.execution_simulator
        )

        try:
            loop.run()
        except KeyboardInterrupt:
            loop.set_is_running(False)

    def run_distributed(self) -> Any:
        # TODO resource spec for workers
        actors = [SimulationWorkerActor.remote(num_cpus=1) for _ in range(len(self.generators))]

        refs = [actors[i].run_loop.remote(Loop(
            clock=Clock(-1),
            data_generator=self.generators[i],
            portfolio=self.portfolio,
            strategy=self.strategy,
            execution_simulator=self.execution_simulator
        )) for i in range(len(actors))]

        # wait for all runs to finish
        ray.get(refs)
        stats = ray.get([actor.get_run_stats.remote() for actor in actors])
        return self._aggregate_stats(stats)

    def _aggregate_stats(self, stats: List[Any]) -> Any:
        pass # TODO

if __name__ == '__main__':
    clock = Clock(-1)
    # generator = FeatureStreamGenerator(featurizer_config=None)
    instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
    generator = SineDataGenerator(instrument, 0, 100000, 1)
    portfolio = Portfolio.load_config('portfolio-config.yaml')
    strategy = BuyLowSellHighStrategy(instrument=instrument, clock=clock, portfolio=portfolio, params={
        'buy_signal_thresh': 0.05,
        'sell_signal_thresh': 0.05,
    })
    execution_simulator = ExecutionSimulator(clock, portfolio, generator)
    loop = Loop(
        clock=clock,
        data_generator=generator,
        portfolio=portfolio,
        strategy=strategy,
        execution_simulator=execution_simulator
    )

    runner = SimulationRunner(
        generators=[generator],
        portfolio=portfolio,
        strategy=strategy,
        execution_simulator=execution_simulator
    )
    runner.run_single()
