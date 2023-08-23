import unittest

import matplotlib.pyplot as plt
import pandas as pd

from simulation.data.sine.sine_data_generator import SineDataGenerator
from simulation.models.instrument import Instrument


class TestSineDataGenerator(unittest.TestCase):

    def test_gen(self):
        instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
        g = SineDataGenerator(instrument, 0, 100000, 1)

        events = []
        # for _ in range(10000):
        while g.has_next():
            e = g.next()
            if e is not None:
                events.append(e)

        ts = list(map(lambda e: e['timestamp'], events))
        mid_price = list(map(lambda e: e['mid_price'], events))
        df = pd.DataFrame({'timestamp': ts, 'mid_price': mid_price})
        df.plot(x='timestamp', y='mid_price')
        plt.show()
        # plot_multi(col_names=['mid_price'], df=df)


if __name__ == '__main__':
    # unittest.main()
    t = TestSineDataGenerator()
    t.test_gen()