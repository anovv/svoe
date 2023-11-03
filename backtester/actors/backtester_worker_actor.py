import time
from typing import Dict, Type, List, Optional

from featurizer.config import FeaturizerConfig
from backtester.clock import Clock
from featurizer.feature_stream.feature_stream_generator import FeatureStreamGenerator
from backtester.execution.execution_simulator import ExecutionSimulator
from backtester.inference.inference_loop import InferenceConfig
from backtester.loop.loop import Loop, LoopRunResult

import ray

from backtester.models.instrument import Instrument
from backtester.models.portfolio import Portfolio
from backtester.strategy.base import BaseStrategy


# TODO re blocking calls
# https://stackoverflow.com/questions/56556905/remote-calls-are-blocking-when-used-on-methods-in-an-actor-object

@ray.remote
class BacktesterWorkerActor:

    # TODO proper pass inference_config
    def __init__(
        self,
        worker_id: int,
        featurizer_config: FeaturizerConfig,
        portfolio: Portfolio,
        strategy_class: Type[BaseStrategy],
        strategy_params: Optional[Dict],
        tradable_instruments: Optional[List[Instrument]],
        inference_config: Optional[InferenceConfig]
    ):
        self.worker_id = worker_id
        clock = Clock(-1)
        strategy: BaseStrategy = strategy_class(
            clock=clock,
            portfolio=portfolio,
            instruments=tradable_instruments,
            params=strategy_params,
            inference_config=inference_config
        )

        # TODO check if generator is empty
        data_generator = FeatureStreamGenerator(featurizer_config=featurizer_config)
        self.loop = Loop(
            clock=clock,
            feature_generator=data_generator,
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
