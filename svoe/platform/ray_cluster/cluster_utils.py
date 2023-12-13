# remote client tutorial
# https://docs.ray.io/en/master/cluster/running-applications/job-submission/ray-client.html#how-do-you-use-the-ray-client

import ray
from svoe import featurizer
from svoe.platform import ray_cluster
import os
import ray.util
from ray.util.client import ray as ray_util_client

from typing import Optional
from ray._private.worker import BaseContext


# TODO use Ray Jobs
def connect(address: Optional[str] = 'ray://127.0.0.1:10001') -> Optional[BaseContext]:
    # TODO is this a hack?
    os.environ['RAY_IGNORE_VERSION_MISMATCH'] = '1'
    if ray_util_client.is_connected():
        # ray.util.disconnect() # TODO disconnect?
        print('Already connected')
        return None # TODO return exisitng context ?
    # if ray.is_initialized: # TODO or this?
    #     ray.shutdown()
    return ray.init(address=address, runtime_env={
        'py_modules': [featurizer, ray_cluster],

        'env_vars': {
            'AWS_ACCESS_KEY_ID': os.environ['AWS_KEY'],
            'AWS_SECRET_ACCESS_KEY': os.environ['AWS_SECRET'],
            'AWS_DEFAULT_REGION': 'ap-northeast-1'
        },
})

