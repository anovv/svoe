import time
import unittest

import ray

@ray.remote(resources={'worker_size_large': 1, 'instance_spot': 1})
class LargeSpotActor:

    def run(self):
        time.sleep(1000)


@ray.remote(resources={'worker_size_small': 1, 'instance_on_demand': 1})
class SmallOnDemandActor:

    def run(self):
        time.sleep(1000)


class TestCatalogCryptotickPipeline(unittest.TestCase):

    def test_autoscaler(self):

        with ray.init(address='ray://127.0.0.1:10003'):
            for _ in range(10):
                large = LargeSpotActor.remote()
                large.run.remote()
                # small = SmallOnDemandActor.remote()
                # small.run.remote()
            # time.sleep(5)
            # ray.autoscaler.sdk.request_resources(num_cpus=10)
            time.sleep(1000)


if __name__ == '__main__':
    t = TestCatalogCryptotickPipeline()
    t.test_autoscaler()