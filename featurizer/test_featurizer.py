import unittest
import ray

from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer
from common.pandas.df_utils import concat


class TestFeaturizer(unittest.TestCase):

    def test_fl_set(self):
        config_path = 'test_configs/feature-label-set.yaml'
        config = FeaturizerConfig.load_config(path=config_path)
        Featurizer.run(config, ray_address='auto', parallelism=12)

        with ray.init(address='auto', ignore_reinit_error=True):
            refs = Featurizer.get_result_refs()
            df = concat(ray.get(refs))
            print(df.head())
            print(df.tail())


if __name__ == '__main__':
    t = TestFeaturizer()
    t.test_fl_set()