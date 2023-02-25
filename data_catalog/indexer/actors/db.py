from typing import Optional, Dict, List

import ray

from data_catalog.indexer.models import InputItem, IndexItemBatch
from data_catalog.indexer.sql.client import MysqlClient


@ray.remote
class DbActor:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    def _check_exists(self, input_batch) -> List[InputItem]:
        self.client.create_tables()
        to_download_batch = self.client.check_exists(input_batch)
        return to_download_batch

    def _write_batch(self, batch: IndexItemBatch) -> Dict:
        self.client.create_tables()
        self.client.write_index_item_batch(batch)
        # TODO return status to pass to update_progress
        return {}


@ray.remote
def check_exists(db_actor: DbActor, input_batch) -> List[InputItem]:
    print('Checking batch exists...')
    res = ray.get(db_actor._check_exists.remote(input_batch))
    print('Checked batch')
    return res


@ray.remote
def write_batch(db_actor: DbActor, batch: IndexItemBatch) -> Dict:
    print('Writing batch...')
    res = ray.get(db_actor._write_batch.remote(batch))
    print('Written batch to DB')
    return res

