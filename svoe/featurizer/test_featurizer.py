import unittest
import ray

from svoe.featurizer.config import FeaturizerConfig
from svoe.featurizer.runner import Featurizer


class TestFeaturizer(unittest.TestCase):

    def test_fl_set(self):
        config_path = 'test_configs/feature-label-set.yaml'
        # config_path = 'test_configs/synthetic-sine-data-config.yaml'
        config = FeaturizerConfig.load_config(path=config_path)
        ray_address = 'ray://127.0.0.1:10001'
        # Featurizer.run(config, ray_address=ray_address, parallelism=10)

        with ray.init(address=ray_address, ignore_reinit_error=True):
            # df = Featurizer.get_materialized_data(pick_every_nth_row=1000)
            df = Featurizer.get_materialized_data()
            print(df.head())
            print(df.tail())

            df1 = df[df['label_SyntheticSineMidPrice_e7d3822d-mid_price'].between(10740.058490, 10740.058492)]
            df2 = df[df['data_source_SyntheticSineMidPrice_1df609c5-mid_price'].between(10740.058490, 10740.058492)]
            ts1 = df1['timestamp'].iloc[0]
            ts2 = df2['timestamp'].iloc[0]

            print(ts1, ts2, ts2 - ts1)
            # filtering data
            # print(ts1)
            # ts2 = df[df['data_source_SyntheticSineMidPrice_1df609c5-mid_price'] == 10740.058491]['timestamp']
            # print(ts1 - ts2, ts1, ts2)
            # plot_multi(df=df)


if __name__ == '__main__':
    t = TestFeaturizer()
    t.test_fl_set()