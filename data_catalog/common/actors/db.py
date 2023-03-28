from typing import Optional, Dict

import ray

from data_catalog.common.data_models.models import IndexItemBatch, InputItemBatch
from data_catalog.common.utils.sql.client import MysqlClient


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
    # TODO debug sqlalchemy.exc.IntegrityError: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'l2_book-BINANCE-spot-{}-BTC-USDT-BTC-USDT-1641113668.511-1641113' for key 'data_catalog.PRIMARY'")
    def _write_batch(self, batch: IndexItemBatch) -> Dict:
        self.client.create_tables()
        self.client.write_index_item_batch(batch)
        # TODO return status to pass to stats actor
        return {}


