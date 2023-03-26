import time
from typing import Optional, Dict

import ray

# from data_catalog.indexer.actors.stats import Stats, WRITE_DB, FILTER_BATCH, FILTER_TASK_TYPE, WRITE_DB_TASK_TYPE
from data_catalog.indexer.models import IndexItemBatch, InputItemBatch
from data_catalog.utils.register import EventType, report_stats_decor
from data_catalog.utils.sql.client import MysqlClient


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


# TODO we can add actor method ad as DAG node directly https://docs.ray.io/en/latest/ray-core/ray-dag.html#ray-dag-guide
# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.FINISHED])
def filter_existing(db_actor: DbActor, input_batch: InputItemBatch, stats: 'Stats', task_id: str, extra: Optional[Dict] = None) -> InputItemBatch:
    res = ray.get(db_actor._filter_batch.remote(input_batch))
    return res
    # print('Filtering batch...')
    # res = ray.get(db_actor._filter_batch.remote(input_batch))
    # print('Filtered batch')
    # event = {
    #     'task_id': task_id,
    #     'event_type': FILTER_BATCH,
    #     'timestamp': time.time()
    # }
    # stats.event.remote(FILTER_TASK_TYPE, event)
    # return res


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
@report_stats_decor([EventType.FINISHED])
def write_batch(db_actor: DbActor, batch: IndexItemBatch, stats: 'Stats', task_id: str, extra: Optional[Dict] = None) -> Dict:
    # print('Writing batch...')
    # print(batch)
    res = ray.get(db_actor._write_batch.remote(batch))
    # event = {
    #     'task_id': task_id,
    #     'event_type': WRITE_DB,
    #     'timestamp': time.time()
    # }
    # stats.event.remote(WRITE_DB_TASK_TYPE, event)
    return res

