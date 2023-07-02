import unittest
import ray

from featurizer.actors.cache_actor import get_cache_actor
from featurizer.runner import Featurizer
from utils.pandas.df_utils import concat


class TestFeaturizer(unittest.TestCase):

    def test_fl_set(self):
        config_path = 'test_configs/feature-label-set.yaml'
        refs = Featurizer.run(config_path)

        with ray.init(address='auto', ignore_reinit_error=True):
            cache_actor = get_cache_actor()
            print(ray.get(cache_actor.get_cache.remote()))

            # TODO we are note able to access objrefs from prev session
            # TODO figure out how to share data between sessions
            df = concat(ray.get(refs))
        # print(df.head())
        # print(df.tail())


if __name__ == '__main__':
    t = TestFeaturizer()
    t.test_fl_set()