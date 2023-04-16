from data_catalog.common.actors.db import DbActor
from data_catalog.common.actors.stats import Stats
from data_catalog.common.data_models.models import InputItemBatch


class Dag:

    def get(self, dag_id: str, input_batch: InputItemBatch, stats: Stats, db_actor: DbActor):
        raise NotImplemented