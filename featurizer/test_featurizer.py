import unittest
import ray

from featurizer.manager import FeaturizerManager
from utils.pandas.df_utils import concat


class TestFeaturizer(unittest.TestCase):

    def test_fl_set(self):
        config_path = 'test_configs/feature-label-set.yaml'
        refs = FeaturizerManager.run(config_path)

        df = concat(ray.get(refs))
        print(df.head())
        print(df.tail())


if __name__ == '__main__':
    t = TestFeaturizer()
    t.test_fl_set()