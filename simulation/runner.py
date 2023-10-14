import time
from typing import List, Any, Dict, Type, Tuple, Optional

import ray
import yaml
from ray.util import placement_group, remove_placement_group
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy
from featurizer.config import FeaturizerConfig, split_featurizer_config
from simulation.actors.simulation_worker_actor import SimulationWorkerActor
from simulation.clock import Clock
from simulation.data.feature_stream.feature_stream_generator import FeatureStreamGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.inference.inference_loop import InferenceConfig
from simulation.loop.loop import Loop, LoopRunResult
from simulation.models.instrument import Instrument
from simulation.models.portfolio import Portfolio, PortfolioBalanceRecord
from simulation.models.trade import Trade
from simulation.strategy.base import BaseStrategy
from simulation.strategy.buy_low_sell_high import BuyLowSellHighStrategy

import simulation, common, featurizer, client
from simulation.strategy.ml_strategy import MLStrategy
from simulation.viz.visualizer import Visualizer


class SimulationRunner:

    def __init__(
        self,
        featurizer_config: FeaturizerConfig,
        portfolio: Portfolio,
        strategy_class: Type[BaseStrategy],
        strategy_params: Dict,
        tradable_instruments: List[Instrument],
        inference_config: Optional[InferenceConfig],
    ):
        # TODO configify?
        self.featurizer_config = featurizer_config
        self.portfolio = portfolio
        self.strategy_class = strategy_class
        self.strategy_params = strategy_params
        self.tradable_instruments = tradable_instruments
        self.inference_config = inference_config

    def run_locally(self) -> LoopRunResult:
        clock = Clock(-1)
        # TODO proper pass inference_config
        strategy: BaseStrategy = self.strategy_class(
            instruments=self.tradable_instruments,
            clock=clock,
            portfolio=self.portfolio,
            params=self.strategy_params,
            inference_config=self.inference_config
        )
        data_generator = FeatureStreamGenerator(featurizer_config=self.featurizer_config)
        loop = Loop(
            clock=clock,
            data_generator=data_generator,
            portfolio=self.portfolio,
            strategy=strategy,
            execution_simulator=ExecutionSimulator(clock, self.portfolio, data_generator)
        )
        try:
            return loop.run()
        except KeyboardInterrupt:
            loop.stop()

    def run_remotely(self, ray_address: str, num_workers: int) -> Any:
        with ray.init(address=ray_address, ignore_reinit_error=True, runtime_env={
            'pip': ['xgboost', 'xgboost_ray', 'mlflow', 'diskcache', 'pyhumps'],
            'py_modules': [simulation, common, featurizer, client],

        }):
            print(f'Starting distributed run with {num_workers} workers...')
            # TODO resource spec for workers
            # TODO verify cluster has enough resources (also consider mem, custom resource, etc.)
            print(ray.available_resources())

            pg = placement_group(bundles=[{'CPU': 0.9} for _ in range(num_workers)], strategy='SPREAD')
            ready, unready = ray.wait([pg.ready()], timeout=10)
            if unready:
                raise ValueError(f'Unable to create placement group for {num_workers} workers')

            featurizer_configs = split_featurizer_config(self.featurizer_config, num_workers)

            # TODO proper pass inference_config
            actors = [SimulationWorkerActor.options(
                num_cpus=0.9,
                max_concurrency=10, # wuut?
                scheduling_strategy=PlacementGroupSchedulingStrategy(
                    placement_group=pg,
                    placement_group_capture_child_tasks=True
            )).remote(
                worker_id=i,
                featurizer_config=featurizer_configs[i],
                portfolio = self.portfolio,
                strategy_class = self.strategy_class,
                strategy_params = self.strategy_params,
                tradable_instruments = self.tradable_instruments,
                inference_config=self.inference_config
            ) for i in range(num_workers)]

            print(f'Inited {len(actors)} worker actors')
            refs = [actors[i].run_loop.remote() for i in range(len(actors))]
            print(f'Scheduled loops, waiting for finish...')

            # wait for all runs to finish
            results = ray.get(refs)
            remove_placement_group(pg)
            return self._aggregate_loop_run_results(results)

    # TODO this should be udf
    # TODO make separate dataclass for distributed run result?
    def _aggregate_loop_run_results(self, results: List[LoopRunResult]) -> LoopRunResult:
        # results should be already ordered
        agg_trades: Dict[Instrument, List[Trade]] = {} # should be dict
        agg_balances: List[PortfolioBalanceRecord] = []
        agg_prices: Dict[Instrument, List[Tuple[float, float]]] = {} # should be dict
        agg_inferences: List[Tuple[Any, float]] = []
        # TODO proper aggregation
        for res in results:
            for instrument in res.executed_trades:
                if instrument in agg_trades:
                    agg_trades[instrument].extend(res.executed_trades[instrument])
                else:
                    agg_trades[instrument] = res.executed_trades[instrument]

            agg_balances.extend(res.portfolio_balances)

            for instrument in res.executed_trades:
                if instrument in agg_prices:
                    agg_prices[instrument].extend(res.sampled_prices[instrument])
                else:
                    agg_prices[instrument] = res.sampled_prices[instrument]

            agg_inferences.extend(res.inference_results)

        return LoopRunResult(
            executed_trades=agg_trades,
            portfolio_balances=agg_balances,
            sampled_prices=agg_prices,
            inference_results=agg_inferences
        )

def test_buy_low_sell_high():
    featurizer_config_raw = yaml.safe_load(open('./data/feature_stream/test-featurizer-config.yaml', 'r'))
    featurizer_config = FeaturizerConfig(**featurizer_config_raw)
    # TODO derive from featurizer_config
    tradable_instruments = [
        Instrument('BINANCE', 'spot', 'BTC-USDT'),
        Instrument('BINANCE', 'spot', 'ETH-USDT'),
        Instrument('BINANCE', 'spot', 'SOL-USDT'),
        Instrument('BINANCE', 'spot', 'XRP-USDT'),
    ]
    # TODO derive from featurizer_config
    portfolio = Portfolio.load_config('portfolio-config.yaml')
    strategy_params = {
        'buy_signal_thresh': 0.05,
        'sell_signal_thresh': 0.05,
    }

    runner = SimulationRunner(
        featurizer_config=featurizer_config,
        portfolio=portfolio,
        strategy_class=BuyLowSellHighStrategy,
        strategy_params=strategy_params,
        tradable_instruments=tradable_instruments,
        inference_config=None
    )

    start = time.time()
    # result = runner.run_locally()
    result = runner.run_remotely('ray://127.0.0.1:10001', 4)
    print(f'Finished run in {time.time() - start}s')
    viz = Visualizer(result)

    # TODO add inference results
    viz.visualize(instruments=tradable_instruments)


def test_ml():
    featurizer_config_raw = yaml.safe_load(open('./data/feature_stream/test-featurizer-config.yaml', 'r'))
    featurizer_config = FeaturizerConfig(**featurizer_config_raw)
    # TODO derive from featurizer_config
    tradable_instruments = [
        Instrument('BINANCE', 'spot', 'BTC-USDT'),
    ]
    # TODO derive from featurizer_config
    portfolio = Portfolio.load_config('portfolio-config.yaml')
    strategy_params = {
        'buy_delta': 0,
        'sell_delta': 0,
    }

    inference_config = InferenceConfig(
        deployment_name='test-deployment',
        model_uri='/tmp/svoe/mlflow/mlruns/1/211408db196847e2befc331887450660/artifacts/checkpoint_000010',
        predictor_class_name='XGBoostPredictor',
        num_replicas=1
    )

    runner = SimulationRunner(
        featurizer_config=featurizer_config,
        portfolio=portfolio,
        strategy_class=MLStrategy,
        strategy_params=strategy_params,
        tradable_instruments=tradable_instruments,
        inference_config=inference_config
    )

    start = time.time()
    result = runner.run_locally()
    # result = runner.run_remotely('ray://127.0.0.1:10001', 4)
    print(f'Finished run in {time.time() - start}s')
    viz = Visualizer(result)

    # TODO add inference results
    viz.visualize(instruments=tradable_instruments)

if __name__ == '__main__':
    test_ml()