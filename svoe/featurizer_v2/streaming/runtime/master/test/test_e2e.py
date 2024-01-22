import logging
import time
import unittest
from pathlib import Path

import ray
import yaml

from svoe.featurizer_v2.streaming.api.context.streaming_context import StreamingContext


class TestE2E(unittest.TestCase):

    def test_sample_stream(self):
        ray.init(address='auto')
        job_config = yaml.safe_load(Path('../../sample-job-config.yaml').read_text())
        ctx = StreamingContext(job_config=job_config)
        ctx.from_values('a', 'b', 'c') \
            .map(lambda x: (x, 1)) \
            .key_by(lambda x: x[0]) \
            .sink(lambda x: print(x))

        ctx.submit()

        time.sleep(1000)

        ray.shutdown()


if __name__ == '__main__':
    t = TestE2E()
    t.test_sample_stream()