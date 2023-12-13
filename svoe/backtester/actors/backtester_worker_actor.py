import time
from typing import Dict, Type, List, Optional

from svoe.featurizer.config import FeaturizerConfig
from svoe.backtester.clock import Clock
from svoe.featurizer.streaming.offline_feature_stream_generator import OfflineFeatureStreamGenerator
from svoe.backtester.execution.execution_simulator import ExecutionSimulator
from svoe.backtester.inference.inference_loop import InferenceConfig
from svoe.backtester.loop.loop import Loop, LoopRunResult

import ray

from svoe.backtester.models.instrument import Instrument
from svoe.backtester.models.portfolio import Portfolio
from svoe.backtester.strategy.base import BaseStrategy


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
        data_generator = OfflineFeatureStreamGenerator(featurizer_config=featurizer_config)
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
