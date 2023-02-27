from typing import Optional, Dict, List

import ray

from data_catalog.indexer.actors.stats import Stats, WRITE_DB, FILTER_BATCH
from data_catalog.indexer.models import IndexItemBatch, InputItemBatch
from data_catalog.indexer.sql.client import MysqlClient


@ray.remote
class DbActor:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    # TODO asyncify this
    def _filter_batch(self, input_batch: InputItemBatch) -> InputItemBatch:
        self.client.create_tables()
        to_download_batch = self.client.filter_batch(input_batch)
        return to_download_batch

    # TODO asyncify this
    def _write_batch(self, batch: IndexItemBatch) -> Dict:
        self.client.create_tables()
        self.client.write_index_item_batch(batch)
        # TODO return status to pass to stats actor
        return {}


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def filter_existing(db_actor: DbActor, input_batch: InputItemBatch, stats: Stats) -> InputItemBatch:
    print('Filtering batch...')
    res = ray.get(db_actor._filter_batch.remote(input_batch))
    print('Filtered batch')
    stats.inc_counter.remote(FILTER_BATCH)
    return res


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def write_batch(db_actor: DbActor, batch: IndexItemBatch, stats: Stats) -> Dict:
    print('Writing batch...')
    print(batch)
    res = ray.get(db_actor._write_batch.remote(batch))
    stats.inc_counter.remote(WRITE_DB)
    return res

