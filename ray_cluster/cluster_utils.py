# remote client tutorial
# https://docs.ray.io/en/master/cluster/running-applications/job-submission/ray-client.html#how-do-you-use-the-ray-client

import ray
import featurizer
import ray_cluster
import os
import ray.util
from ray.util.client import ray as ray_util_client

from typing import Optional, Dict
from ray._private.worker import BaseContext


# TODO use Ray Jobs
def connect(address: Optional[str] = 'ray://127.0.0.1:10001') -> Optional[BaseContext]:
    if ray_util_client.is_connected():
        # ray.util.disconnect() # TODO disconnect?
        print('Already connected')
        return None
    return ray.init(address=address, runtime_env={
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
# ray.get_runtime_context()

