from streamz import Stream

from simulation.loop.loop import Loop
from simulation.strategy.buy_and_hold import BuyAndHoldStrategy

if __name__ == '__main__':
    # loop = Loop(featurizer_config=None, portfolio_config={}, strategy_class=BuyAndHoldStrategy)
    #
    # try:
    #     loop.run()
    # except KeyboardInterrupt:
    #     loop.set_is_running(False)

    def increment(x):
        return x + 1


    def decrement(x):
        return x - 1


    # source = Stream()
    # a = source.map(increment)
    # b = source.map(decrement)
    # c = a.zip(b).sink(print)
    #
    # source.emit(1)
    # source.emit(2)

    a = Stream()
    b = Stream()
    c = Stream()

    l = []

    def flatten(data):
        if isinstance(data, tuple):
            if len(data) == 0:
                return ()
            else:
                return flatten(data[0]) + flatten(data[1:])
        else:
            return (data,)

    def appnd(t):
        r = flatten(t)
        l.append(r)


    # d = a.combine_latest(b).combine_latest(c).sink(appnd)
    d = a.zip(b).zip(c).sink(appnd)
    a.emit(1)
    b.emit(2)
    c.emit(3)
    a.emit(4)
    b.emit(5)
    c.emit(6)

    print(l)