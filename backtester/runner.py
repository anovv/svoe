import time
from typing import List, Any, Dict, Type, Tuple, Optional

import ray
import yaml
from pydantic import BaseModel
from ray.util import placement_group, remove_placement_group
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy

from common.common_utils import load_class_by_name
from featurizer.config import FeaturizerConfig, split_featurizer_config
from backtester.actors.backtester_worker_actor import BacktesterWorkerActor
from backtester.clock import Clock
from featurizer.feature_stream.offline_feature_stream_generator import OfflineFeatureStreamGenerator
from backtester.execution.execution_simulator import ExecutionSimulator
from backtester.inference.inference_loop import InferenceConfig
from backtester.loop.loop import Loop, LoopRunResult
from backtester.models.instrument import Instrument
from backtester.models.portfolio import Portfolio, PortfolioBalanceRecord
from backtester.models.trade import Trade
from backtester.strategy.base import BaseStrategy
from backtester.strategy.buy_low_sell_high import BuyLowSellHighStrategy

import backtester, common, featurizer, client
from backtester.strategy.ml_strategy import MLStrategy
from backtester.viz.visualizer import Visualizer


class BacktesterConfig(BaseModel):
    featurizer_config: Optional[FeaturizerConfig]
    featurizer_config_path: Optional[str]
    portfolio: Optional[Portfolio]
    portfolio_path: Optional[str]
    inference_config: Optional[InferenceConfig]
    inference_config_path: Optional[str]
    tradable_instruments_params: Optional[List[Dict]]
    tradable_instruments: Optional[List[Instrument]]
    strategy_class: Optional[Type[BaseStrategy]]
    strategy_class_name: Optional[str]
    strategy_params: Optional[Dict]

    @classmethod
    def load_config(cls, path: str) -> 'BacktesterConfig':

        with open(path, 'r') as stream:
            d = yaml.safe_load(stream)
            c = BacktesterConfig.parse_obj(d)
            if c.featurizer_config_path is not None:
                if c.featurizer_config is not None:
                    raise ValueError('Provide either featurizer_config or featurizer_config_path')
                c.featurizer_config = FeaturizerConfig.load_config(c.featurizer_config_path)

            if c.portfolio_path is not None:
                if c.portfolio is not None:
                    raise ValueError('Provide either portfolio_path or portfolio')
                c.portfolio = Portfolio.load_config(c.portfolio_path)

            if c.inference_config_path is not None:
                if c.inference_config is not None:
                    raise ValueError('Provide either inference_config_path or inference_config')
                c.inference_config = InferenceConfig.load_config(c.inference_config_path)

            if c.strategy_class_name is not None:
                if c.strategy_class is not None:
                    raise ValueError('Provide either strategy_class_name or strategy_class')
                c.strategy_class = load_class_by_name(c.strategy_class_name)

            if c.tradable_instruments_params is not None:
                if c.tradable_instruments is not None:
                    raise ValueError('Provide either tradable_instruments or tradable_instruments_params')

                c.tradable_instruments = list(map(lambda d: Instrument(**d), c.tradable_instruments_params))

            return c


class Backtester:

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


    @classmethod
    def from_config(cls, backtester_config: BacktesterConfig) -> 'Backtester':
        return Backtester(
            featurizer_config=backtester_config.featurizer_config,
            portfolio=backtester_config.portfolio,
            strategy_class=backtester_config.strategy_class,
            strategy_params=backtester_config.strategy_params,
            tradable_instruments=backtester_config.tradable_instruments,
            inference_config=backtester_config.inference_config
        )

    def run_locally(self) -> LoopRunResult:
        clock = Clock(-1)
        strategy: BaseStrategy = self.strategy_class(
            instruments=self.tradable_instruments,
            clock=clock,
            portfolio=self.portfolio,
            params=self.strategy_params,
            inference_config=self.inference_config
        )
        data_generator = OfflineFeatureStreamGenerator(featurizer_config=self.featurizer_config)
        loop = Loop(
            clock=clock,
            feature_generator=data_generator,
            portfolio=self.portfolio,
            strategy=strategy,
            execution_simulator=ExecutionSimulator(clock, self.portfolio, data_generator)
        )
        try:
            return loop.run()
        except KeyboardInterrupt:
            loop.stop()

    def run_remotely(self, ray_address: str, num_workers: int) -> Any:
        # TODO this is not needed for local env
        with ray.init(address=ray_address, ignore_reinit_error=True, runtime_env={
            'pip': ['xgboost', 'xgboost_ray', 'mlflow', 'diskcache', 'pyhumps'],
            'py_modules': [backtester, common, featurizer, client],

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

            actors = [BacktesterWorkerActor.options(
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
    featurizer_config_raw = yaml.safe_load(open('../featurizer/feature_stream/test-featurizer-config.yaml', 'r'))
    featurizer_config = FeaturizerConfig(**featurizer_config_raw)
    # TODO derive from featurizer_config
    tradable_instruments = [
        Instrument('BINANCE', 'spot', 'BTC-USDT'),
        Instrument('BINANCE', 'spot', 'ETH-USDT'),
        Instrument('BINANCE', 'spot', 'SOL-USDT'),
        Instrument('BINANCE', 'spot', 'XRP-USDT'),
    ]
    # TODO derive from featurizer_config
    portfolio = Portfolio.load_config('sample_configs/portfolio-config.yaml')
    strategy_params = {
        'buy_signal_thresh': 0.05,
        'sell_signal_thresh': 0.05,
    }

    backtester = Backtester(
        featurizer_config=featurizer_config,
        portfolio=portfolio,
        strategy_class=BuyLowSellHighStrategy,
        strategy_params=strategy_params,
        tradable_instruments=tradable_instruments,
        inference_config=None
    )

    start = time.time()
    # result = backtester.run_locally()
    result = backtester.run_remotely('ray://127.0.0.1:10001', 4)
    print(f'Finished run in {time.time() - start}s')
    viz = Visualizer(result)

    # TODO add inference results
    viz.visualize(instruments=tradable_instruments)


def test_ml():
    featurizer_config_raw = yaml.safe_load(open('../featurizer/feature_stream/test-featurizer-config.yaml', 'r'))
    featurizer_config = FeaturizerConfig(**featurizer_config_raw)
    # TODO derive from featurizer_config
    tradable_instruments = [
        Instrument('BINANCE', 'spot', 'BTC-USDT'),
    ]
    # TODO derive from featurizer_config
    portfolio = Portfolio.load_config('sample_configs/portfolio-config.yaml')
    strategy_params = {
        'buy_delta': 0,
        'sell_delta': 0,
    }

    inference_config = InferenceConfig(
        deployment_name='test-deployment',
        model_uri='file:///tmp/svoe/mlflow/mlruns/1/d6e5eccdfedf43f8acd966e4d6d331a4/artifacts/checkpoint_000010',
        predictor_class_name='XGBoostPredictor',
        num_replicas=1
    )

    backtester = Backtester(
        featurizer_config=featurizer_config,
        portfolio=portfolio,
        strategy_class=MLStrategy,
        strategy_params=strategy_params,
        tradable_instruments=tradable_instruments,
        inference_config=inference_config
    )

    start = time.time()
    result = backtester.run_locally()
    # result = backtester.run_remotely('ray://127.0.0.1:10001', 4)
    print(f'Finished run in {time.time() - start}s')
    viz = Visualizer(result)

    # TODO add inference results
    viz.visualize(instruments=tradable_instruments)


if __name__ == '__main__':
    # test_ml()
    test_buy_low_sell_high()