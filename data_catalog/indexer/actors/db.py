from typing import Optional, Dict

from ray.util.client import ray

from data_catalog.indexer.actors.queues import InputQueue, DownloadQueue, StoreQueue
from data_catalog.indexer.indexer import Coordinator
from data_catalog.indexer.models import IndexItemBatch
from data_catalog.indexer.sql.client import MysqlClient


@ray.remote
class DbReader:
    def __init__(self, input_queue: InputQueue, download_queue: DownloadQueue, db_config: Optional[Dict] = None):
        self.input_queue = input_queue
        self.download_queue = download_queue
        self.client = MysqlClient(db_config)

    def run(self):
        self.input_batch_ref = self.input_queue.pop()
        while True:
            input_batch = ray.get(self.input_batch_ref)
            if input_batch is None:
                # TODO add sleep so we don't waste CPU cycles
                continue

            # schedule async fetching of next work item to enable compute pipelining
            self.input_batch_ref = self.input_queue.pop()
            # work item is a batch of input items to check if they are already indexed
            to_download_batch = self.client.check_exists(input_batch)
            # fire and forget put, don't call ray.get
            self.download_queue.put(to_download_batch)


@ray.remote
class DbWriter:
    def __init__(self, coordinator: Coordinator, store_queue: StoreQueue, db_config: Optional[Dict] = None):
        self.coordinator = coordinator
        self.store_queue = store_queue
        self.client = MysqlClient(db_config)

    def write_batch(self, batch: IndexItemBatch) -> Dict:
        self.client.create_tables()
        self.client.write_index_item_batch(batch)
        # TODO return status to pass to update_progress on coordinator
        return {}

    def run(self):
        self.index_item_batch_ref = self.coordinator.get_to_write_batch.remote()
        while True:
            index_item_batch = ray.get(self.index_item_batch_ref)
            if index_item_batch is None:
                # TODO sleep here for some time to avoid waisting CPU cycles?
                continue

            # schedule async fetching of next work item to enable compute pipelining
            self.index_item_batch_ref = self.store_queue.pop_with_wait_if_last.remote()
            # work item is a batch of index items to write to DB
            write_status = self.write_batch(index_item_batch)
            # fire and forget put, don't call ray.get
            self.coordinator.update_progress(write_status).remote()