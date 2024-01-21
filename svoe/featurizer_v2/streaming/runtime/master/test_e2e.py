import logging
import time
import unittest

import ray

from svoe.featurizer_v2.streaming.api.context.streaming_context import StreamingContext

logger = logging.getLogger(__name__)


class TestE2E(unittest.TestCase):

    def test_sample_stream(self):
        ray.init()
        ctx = StreamingContext()
        ctx \
        .from_values('a', 'b', 'c') \
        .map(lambda x: (x, 1)) \
        .key_by(lambda x: x[0]) \
        .sink(lambda x: print(x))

        ctx.submit()

        time.sleep(5)

        ray.shutdown()


if __name__ == '__main__':
    t = TestE2E()
    t.test_sample_stream()