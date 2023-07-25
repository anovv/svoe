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

    def flatten_tuples(data):
        if isinstance(data, tuple):
            if len(data) == 0:
                return ()
            else:
                return flatten_tuples(data[0]) + flatten_tuples(data[1:])
        else:
            return (data,)

    def appnd(t):
        r = flatten_tuples(t)
        l.append(r)


    d = a.map(lambda e: ['a', e]).combine_latest(b.map(lambda e: ['b', e])).combine_latest(c.map(lambda e: ['c', e])).sink(appnd)
    # d = a.zip(b).zip(c).sink(appnd)
    a.emit(1)
    b.emit(2)
    c.emit(3)
    # a.emit(4)
    # b.emit(5)
    # c.emit(6)

    print(l)