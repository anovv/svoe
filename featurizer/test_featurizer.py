import unittest
import ray

from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer
from common.pandas.df_utils import concat, plot_multi


class TestFeaturizer(unittest.TestCase):

    def test_fl_set(self):
        config_path = 'test_configs/feature-label-set.yaml'
        # config_path = 'test_configs/synthetic-sine-data-config.yaml'
        config = FeaturizerConfig.load_config(path=config_path)
        ray_address = 'ray://127.0.0.1:10001'
        Featurizer.run(config, ray_address=ray_address, parallelism=10)

        with ray.init(address=ray_address, ignore_reinit_error=True):
            # df = Featurizer.get_materialized_data(pick_every_nth_row=1000)
            df = Featurizer.get_materialized_data(pick_every_nth_row=10)
            print(df.head())
            print(df.tail())
            plot_multi(df=df)


if __name__ == '__main__':
    t = TestFeaturizer()
    t.test_fl_set()