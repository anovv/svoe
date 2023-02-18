import time
from threading import Thread
from typing import List, Tuple, Dict

import pandas as pd
from ray.util.client import ray

from data_catalog.indexer.actors.queues import DownloadQueue, StoreQueue
from data_catalog.indexer.models import InputItem
from data_catalog.indexer.tasks.tasks import load_and_queue_df, index_and_queue_df


@ray.remote
class Coordinator:
    # TODO figure out if its ok to use list here (regarding concurrency/race conditions)
    index_queue: List[Tuple[pd.DataFrame, InputItem]] = []

    def __init__(self, download_queue: DownloadQueue, store_queue: StoreQueue):
        self.download_queue = download_queue
        self.store_queue = store_queue

    def update_progress(self, info: Dict):
        # TODO
        return

    def _schedule_downloads(self):
        # TODO add backpressure to Driver program, stop when driver queue is empty
        # TODO abstract pipelined loop to util methos/class
        def _run_loop():
            self.to_download_ref = self.download_queue.pop.remote()
            while True:
                to_download = ray.get(self.to_download_ref)
                # schedule async fetching of next work item to enable compute pipelining
                self.to_download_ref = self.download_queue.pop.remote()
                if to_download is None:
                    # TODO sleep here for some time to avoid waisting CPU cycles?
                    continue
                # fire and forget
                # TODO set resources
                load_and_queue_df.remote(to_download, self.index_queue)

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
                df_to_index, input_item = self.index_queue.pop(0)
                print('Bam')
                # fire and forget
                # TODO set resources
                index_and_queue_df.remote(df_to_index, input_item, self.store_queue)

        self.i_thread = Thread(target=_run_loop)
        self.i_thread.start()

    # TODO for multi-threaded actor
    # see https://docs.ray.io/en/latest/ray-core/actors/patterns/concurrent-operations-async-actor.html
    # https://stackoverflow.com/questions/54937456/how-to-make-an-actor-do-two-things-simultaneously
    # main coordinator loop
    def run(self):
        self._schedule_downloads()
        self._schedule_indexing()
