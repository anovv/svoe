# remote client tutorial
# https://docs.ray.io/en/master/cluster/running-applications/job-submission/ray-client.html#how-do-you-use-the-ray-client
# TODO use Ray Jobs

import ray
import time
import featurizer
import ray_cluster
import os

@ray.remote
class Counter:
    def __init__(self):
        self.i = 0

    def get(self):
        return self.i

    def incr(self, value):
        self.i += value

# ray.util.disconnect()
# ray.util.connect # TODO ?
ray.init('ray://127.0.0.1:10001', runtime_env={
    'py_modules': [featurizer, ray_cluster],
    # TODO figure out deps
    'pip': [
        'pyarrow',
        's3fs',
        'fastparquet',
        'order-book',
        'awswrangler',
        'boto3',
        'streamz',
        'frozenlist',
        'prefect_aws',
        'prefect_dask',
        'prefect_aws',
        'dask',
        'tqdm',
        'matplotlib',
        'intervaltree'
    ],
    'env_vars': {
        'AWS_ACCESS_KEY_ID': os.environ['AWS_KEY'],
        'AWS_SECRET_ACCESS_KEY': os.environ['AWS_SECRET'],
        'AWS_DEFAULT_REGION': 'ap-northeast-1'
    },
})
ray.get_runtime_context()
c = Counter.remote()

for _ in range(10):
    c.incr.remote(1)

time.sleep(180)

print(ray.get(c.get.remote()))

