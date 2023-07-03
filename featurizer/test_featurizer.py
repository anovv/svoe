import unittest
import ray

from featurizer.actors.cache_actor import get_cache_actor
from featurizer.runner import Featurizer
from utils.pandas.df_utils import concat


class TestFeaturizer(unittest.TestCase):

    def test_fl_set(self):
        config_path = 'test_configs/feature-label-set.yaml'
        Featurizer.run(config_path)

        with ray.init(address='auto', ignore_reinit_error=True):
            cache_actor = get_cache_actor()
            refs = ray.get(cache_actor.get_featurizer_result_refs.remote())
            df = concat(ray.get(refs))
            print(df.head())
            print(df.tail())


if __name__ == '__main__':
    t = TestFeaturizer()
    t.test_fl_set()