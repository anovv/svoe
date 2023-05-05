from featurizer.data_catalog.common.actors.db import DbActor
from featurizer.data_catalog.common.data_models.models import InputItemBatch


class Dag:

    def get(self, dag_id: str, input_batch: InputItemBatch, db_actor: DbActor):
        raise NotImplemented