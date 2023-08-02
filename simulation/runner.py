from simulation.clock import Clock
from simulation.data.feature_stream.feature_stream_generator import FeatureStreamGenerator
from simulation.data.sine.sine_data_generator import SineDataGenerator
from simulation.execution.execution_simulator import ExecutionSimulator
from simulation.loop.loop import Loop
from simulation.models.instrument import Instrument
from simulation.models.portfolio import Portfolio
from simulation.strategy.buy_and_hold import BuyAndHoldStrategy

if __name__ == '__main__':
    clock = Clock(-1)
    # generator = FeatureStreamGenerator(featurizer_config=None)
    instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
    generator = SineDataGenerator(instrument, 0, 100000, 1)
    portfolio = Portfolio.load_config('portfolio-config.yaml')
    strategy = BuyAndHoldStrategy(portfolio=portfolio, predictor_config={})
    execution_simulator = ExecutionSimulator(clock, portfolio, generator)
    loop = Loop(
        clock=clock,
        data_generator=generator,
        portfolio=portfolio,
        strategy=strategy,
        execution_simulator=execution_simulator
    )

    try:
        loop.run()
    except KeyboardInterrupt:
        loop.set_is_running(False)
