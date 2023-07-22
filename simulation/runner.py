from simulation.loop.loop import Loop
from simulation.strategy.buy_and_hold import BuyAndHoldStrategy

if __name__ == '__main__':
    loop = Loop(data_config={}, portfolio_config={}, strategy_class=BuyAndHoldStrategy)

    try:
        loop.run()
    except KeyboardInterrupt:
        loop.set_is_running(False)