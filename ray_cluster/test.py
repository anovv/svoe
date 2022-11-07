# remote client tutorial
# https://docs.ray.io/en/master/cluster/running-applications/job-submission/ray-client.html#how-do-you-use-the-ray-client
# TODO use Ray Jobs

import ray
import time

ADDRESS = 'ray://127.0.0.1:10001'

@ray.remote
class Counter:
    def __init__(self):
        self.i = 0

    def get(self):
        return self.i

    def incr(self, value):
        self.i += value


ray.init(address=ADDRESS)
c = Counter.remote()

for _ in range(10):
    c.incr.remote(1)

time.sleep(180)

print(ray.get(c.get.remote()))
