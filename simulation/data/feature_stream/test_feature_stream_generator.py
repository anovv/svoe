import time
import unittest

import pandas as pd

from featurizer.config import FeaturizerConfig
from simulation.data.feature_stream.feature_stream_generator import FeatureStreamGenerator

from common.pandas.df_utils import plot_multi


class TestFeatureStreamGenerator(unittest.TestCase):

    def test_gen(self):
        config_path = 'test-featurizer-config.yaml'
        config = FeaturizerConfig.load_config(path=config_path)
        data_generator = FeatureStreamGenerator(config)

        input_events_per_interval = data_generator.input_data_events
        input_events = input_events_per_interval[list(input_events_per_interval.keys())[0]]

        input_ts = list(map(lambda e: e[1]['timestamp'], input_events))
        input_diffs = []
        for i in range(1, len(input_ts)):
            input_diffs.append(input_ts[i] - input_ts[i - 1])

        events = []
        start_ts = time.time()
        # for _ in range(10000):
        while data_generator.has_next():
            e = data_generator.next()
            if e is not None:
                events.append(e)
        print(f'Finished in {time.time() - start_ts}s')

        diffs = []
        for i in range(1, len(events)):
            prev_e = events[i - 1]
            cur_e = events[i]
            prev_ts = prev_e[list(prev_e.keys())[0]]['timestamp']
            cur_ts = cur_e[list(cur_e.keys())[0]]['timestamp']
            diffs.append(cur_ts - prev_ts)

        ts = list(map(lambda e: e[list(e.keys())[0]]['timestamp'], events))
        mid_price = list(map(lambda e: e[list(e.keys())[0]]['mid_price'], events))
        volatility = list(map(lambda e: e[list(e.keys())[1]]['volatility'], events))
        df = pd.DataFrame({'timestamp': ts, 'mid_price': mid_price, 'volatility': volatility})
        plot_multi(df=df, col_names=['mid_price', 'volatility'])

        # plt.hist(diffs, bins=10)
        # plt.hist(input_diffs, bins=100)
        # plt.plot(input_diffs[10:])
        # plt.plot(diffs[10:])
        # plt.show()


if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureStreamGenerator()
    t.test_gen()