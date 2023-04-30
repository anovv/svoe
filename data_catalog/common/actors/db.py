from typing import Optional, Dict, List

import ray

from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.utils.sql.client import MysqlClient
from data_catalog.common.utils.sql.models import DataCatalog


# TODO use max_concurrency=n instead of threads
# @ray.remote(resources={'worker_size_small': 1, 'instance_on_demand': 1})
@ray.remote
class DbActor:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    # TODO asyncify this
    def filter_batch(self, input_batch: InputItemBatch) -> InputItemBatch:
        self.client.create_tables()
        items = input_batch[1]
        if len(items) == 0:
            return input_batch
        source = items[0]['source']
        if source == 'cryptofeed':
            return self.client.filter_cryptofeed_batch(input_batch)
        elif source == 'cryptotick':
            return self.client.filter_cryptotick_batch(input_batch)
        else:
            raise ValueError(f'Unsupported source:{ source}')

    # TODO asyncify this
    def write_batch(self, batch: List[DataCatalog]) -> Dict:
        self.client.create_tables()
        self.client.write_catalog_item_batch(batch)
        # TODO return status to pass to stats actor
        return {}


