import time
from typing import List, Any, Dict

import ray
import yaml
from ray.util import placement_group, remove_placement_group
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy

from featurizer.config import FeaturizerConfig
from simulation.actors.simulation_worker_actor import SimulationWorkerActor
from simulation.clock import Clock
from simulation.data.data_generator import DataStreamGenerator
from simulation.data.feature_stream.feature_stream_generator import FeatureStreamGenerator
from simulation.data.sine.sine_data_generator import SineDataStreamGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.loop.loop import Loop
from simulation.models.instrument import Instrument
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy
from simulation.strategy.buy_low_sell_high import BuyLowSellHighStrategy

import simulation, common


class SimulationRunner:

    def __init__(self, clock: Clock, generators: List[DataStreamGenerator], portfolio: Portfolio, strategy: BaseStrategy):
        # TODO generator creation should be inside actor (since it pulls data from remote store)
        self.clock = clock
        self.generators = generators
        self.portfolio = portfolio
        self.strategy = strategy
        # TODO config?

    def run_single(self):
        loop = Loop(
            clock=self.clock,
            data_generator=self.generators[0],
            portfolio=self.portfolio,
            strategy=self.strategy,
            execution_simulator=ExecutionSimulator(self.clock, self.portfolio, self.generators[0])
        )
        try:
            loop.run()
        except KeyboardInterrupt:
            loop.set_is_running(False)

    def run_distributed(self, ray_address: str) -> Any:
        with ray.init(address=ray_address, ignore_reinit_error=True, runtime_env={
            'pip': ['xgboost', 'xgboost_ray', 'mlflow', 'diskcache'],
            'py_modules': [simulation, common],

        }):
            print(f'Starting distributed run for {len(self.generators)} data splits...')
            # TODO resource spec for workers
            # TODO verify cluster has enough resources (also consider mem, custom resource, etc.)
            print(ray.available_resources())

            num_workers = len(self.generators)
            pg = placement_group(bundles=[{'CPU': 1.0} for _ in range(num_workers)], strategy='SPREAD')
            ready, unready = ray.wait([pg.ready()], timeout=10)
            if unready:
                raise ValueError(f'Unable to create placement group for {num_workers} workers')

            actors = [SimulationWorkerActor.options(
                num_cpus=1,
                max_concurrency=10,
                scheduling_strategy=PlacementGroupSchedulingStrategy(
                    placement_group=pg,
                    placement_group_capture_child_tasks=True
            )).remote() for _ in range(len(self.generators))]

            print(f'Inited {len(actors)} worker actors')
            refs = [actors[i].run_loop.remote(
                loop=Loop(
                    clock=self.clock,
                    data_generator=self.generators[i],
                    portfolio=self.portfolio,
                    strategy=self.strategy,
                    execution_simulator=ExecutionSimulator(self.clock, self.portfolio, self.generators[i])
                ),
                split_id=i
            ) for i in range(len(actors))]
            print(f'Scheduled loops, waiting for finish...')

            # wait for all runs to finish
            ray.get(refs)
            stats = ray.get([actor.get_run_stats.remote() for actor in actors])
            remove_placement_group(pg)
            return self._aggregate_stats(stats)

    def _aggregate_stats(self, stats: List[Dict]) -> Dict:
        for s in stats:
            del s['state_snapshots']
        return {'stats': stats}


def test_single_run():
    featurizer_config_raw = yaml.safe_load(open('./data/feature_stream/test-featurizer-config.yaml', 'r'))
    generator = FeatureStreamGenerator(featurizer_config=FeaturizerConfig(**featurizer_config_raw))
    clock = Clock(-1)
    instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
    # generator = SineDataGenerator.from_time_range(
    #     instrument=instrument,
    #     start_ts=0,
    #     end_ts=1000000,
    #     step=1
    # )
    portfolio = Portfolio.load_config('portfolio-config.yaml')
    strategy = BuyLowSellHighStrategy(instrument=instrument, clock=clock, portfolio=portfolio, params={
        'buy_signal_thresh': 0.05,
        'sell_signal_thresh': 0.05,
    })

    runner = SimulationRunner(
        clock=clock,
        generators=[generator],
        portfolio=portfolio,
        strategy=strategy
    )

    start = time.time()
    print(f'Single run started')
    runner.run_single()
    print(f'Single run finished in {time.time() - start}s')


def test_distributed_run():
    clock = Clock(-1)
    # TODO infer instruments from featurizer
    instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
    # TODO load featurizer_config
    # generators = FeatureStreamGenerator.split(featurizer_config=None, num_splits=4)
    generators = SineDataStreamGenerator.split(
        instrument=instrument,
        start_ts=0,
        end_ts=1000000,
        step=1,
        num_splits=4
    )
    portfolio = Portfolio.load_config('portfolio-config.yaml')
    strategy = BuyLowSellHighStrategy(instrument=instrument, clock=clock, portfolio=portfolio, params={
        'buy_signal_thresh': 0.05,
        'sell_signal_thresh': 0.05,
    })

    runner = SimulationRunner(
        clock=clock,
        generators=generators,
        portfolio=portfolio,
        strategy=strategy,
    )
    res = runner.run_distributed(ray_address='ray://127.0.0.1:10001')
    return res


if __name__ == '__main__':
    test_single_run()
    # res = test_distributed_run()
    # print(res)
