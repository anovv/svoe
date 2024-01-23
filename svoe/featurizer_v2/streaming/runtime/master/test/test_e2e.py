import time
import unittest
from pathlib import Path

import ray
import yaml

from svoe.featurizer_v2.streaming.api.context.streaming_context import StreamingContext
from svoe.featurizer_v2.streaming.api.function.function import SinkToCacheFunction
from svoe.featurizer_v2.streaming.api.stream.sink_cache_actor import SinkCacheActor


class TestE2E(unittest.TestCase):

    def test_sample_stream(self):
        ray.init(address='auto')
        job_config = yaml.safe_load(Path('../../sample-job-config.yaml').read_text())

        def map_func(x):
            import random
            odd = random.randint(0, 1)
            if odd == 1:
                return (x, 1)
            else:
                return (x, 0)

        ctx = StreamingContext(job_config=job_config)
        source = ctx.from_collection([f'a{i}' for i in range(10)])
        # source = ctx.from_timed_collection([f'a{i}' for i in range(10)], 1)
        source.map(map_func) \
            .key_by(lambda x: x[1]) \
            .reduce(lambda x, y: f'{x}_{y}') \
            .sink(lambda x: print(x))

        ctx.submit()

        time.sleep(1000)

        ray.shutdown()

    def test_join_streams(self):
        ray.init(address='auto')
        job_config = yaml.safe_load(Path('../../sample-job-config.yaml').read_text())
        ctx = StreamingContext(job_config=job_config)

        source1 = ctx.from_collection([(i, f'a{i}') for i in range(300)])
        source2 = ctx.from_collection([(i, f'b{i}') for i in range(300)])

        sink_cache = SinkCacheActor.remote()
        sink_function = SinkToCacheFunction(sink_cache)

        s = source1.join(source2)\
            .where_key(lambda x: x[0])\
            .equal_to(lambda x: x[0])\
            .with_func(lambda x, y: (x, y)) \
            .filter(lambda x: x[0] != None and x[1] != None)

        s.sink(sink_function)
        s.sink(lambda x: print(x))

        ctx.submit()

        time.sleep(5)

        res = ray.get(sink_cache.get_values.remote())
        print(res)

        time.sleep(1000)

        ray.shutdown()


if __name__ == '__main__':
    t = TestE2E()
    # t.test_sample_stream()
    t.test_join_streams()