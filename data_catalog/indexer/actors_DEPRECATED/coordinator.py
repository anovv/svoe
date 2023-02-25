import time
from threading import Thread
from typing import List, Tuple, Dict

from ray.types import ObjectRef
from ray.util.client import ray

from data_catalog.indexer.actors.queues import DownloadQueue, StoreQueue
from data_catalog.indexer.actors.stats import Stats
from data_catalog.indexer.models import InputItem
from data_catalog.indexer.tasks.tasks import load_df, index_df


@ray.remote
class Coordinator:
    # TODO figure out if its ok to use list here (regarding concurrency/race conditions)
    index_queue: List[Tuple[ObjectRef, InputItem]] = []

    def __init__(self, stats: Stats, download_queue: DownloadQueue, store_queue: StoreQueue):
        self.stats = stats
        self.download_queue = download_queue
        self.store_queue = store_queue

    def _schedule_downloads(self):
        # TODO add backpressure to Driver program, stop when driver queue is empty
        # TODO abstract pipelined loop to util methos/class
        def _run_loop():
            to_download_ref = self.download_queue.pop.remote()
            while True:
                # TODO implement batch get/pop
                to_download = ray.get(to_download_ref)
                # schedule async fetching of next work item to enable compute pipelining
                to_download_ref = self.download_queue.pop.remote()
                if to_download is None:
                    # TODO sleep here for some time to avoid waisting CPU cycles?
                    continue
                # fire and forget
                # TODO verify resources are optimal
                # TODO use custom download_throughput resource instead on num_cpus (since num_cpus are shared)
                num_cpus = 0.01
                memory_b = to_download['size_kb'] * 20 * 1024 # estimate as x20 of s3 size
                self.index_queue.append((load_df.options(num_cpus=num_cpus, memory=memory_b).remote(to_download, self.stats), to_download))

        self.d_thread = Thread(target=_run_loop)
        self.d_thread.start()

    def _schedule_indexing(self):
        def _run_loop():
            while True:
                if len(self.index_queue) == 0:
                    # sleep to save cpu cycles
                    time.sleep(0.1)
                    continue

                # TODO batch multiple dfs?
                df_to_index_ref, input_item = self.index_queue.pop(0)
                # TODO verify resources are optimal
                num_cpus = 0.9 # leave 0.1 for scheduling I/O tasks
                memory_b = input_item['size_kb'] * 20 * 1024 # estimate as x20 of s3 size
                # fire and forget
                self.store_queue.put.remote(index_df.options(num_cpus=num_cpus, memory=memory_b).remote(df_to_index_ref, input_item, self.stats))

        self.i_thread = Thread(target=_run_loop)
        self.i_thread.start()

    # TODO for multi-threaded actor
    # see https://docs.ray.io/en/latest/ray-core/actors/patterns/concurrent-operations-async-actor.html
    # https://stackoverflow.com/questions/54937456/how-to-make-an-actor-do-two-things-simultaneously
    # main coordinator loop
    def run(self):
        # TODO decouple this into 2 actors?
        # this way we can control download and index throughput
        self._schedule_downloads()
        self._schedule_indexing()
