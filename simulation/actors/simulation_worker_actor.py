import time
from typing import Any, Dict, Type, List

from featurizer.config import FeaturizerConfig
from simulation.clock import Clock
from simulation.data.feature_stream.feature_stream_generator import FeatureStreamGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.loop.loop import Loop, LoopRunResult

import ray

from simulation.models.instrument import Instrument
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy


# TODO re blocking calls
# https://stackoverflow.com/questions/56556905/remote-calls-are-blocking-when-used-on-methods-in-an-actor-object

@ray.remote
class SimulationWorkerActor:

    def __init__(
        self,
        worker_id: int,
        featurizer_config: FeaturizerConfig,
        portfolio: Portfolio,
        strategy_class: Type[BaseStrategy],
        strategy_params: Dict,
        tradable_instruments: List[Instrument]
    ):
        self.worker_id = worker_id
        clock = Clock(-1)
        strategy: BaseStrategy = strategy_class(
            instruments=tradable_instruments,
            clock=clock,
            portfolio=portfolio,
            params=strategy_params
        )

        # TODO check if generator is empty
        data_generator = FeatureStreamGenerator(featurizer_config=featurizer_config)
        self.loop = Loop(
            clock=clock,
            data_generator=data_generator,
            portfolio=portfolio,
            strategy=strategy,
            execution_simulator=ExecutionSimulator(clock, portfolio, data_generator)
        )

    def run_loop(self) -> LoopRunResult:
        start = time.time()
        print(f'[Worker {self.worker_id}] Started loop')
        res = self.loop.run()
        print(f'[Worker {self.worker_id}] Finished loop for split in {time.time() - start}s')
        return res

    # TODO make actor threaded, otherwise calling this won't work due to block from run_loop
    def interrupt_loop(self):
        self.loop.stop()
