from typing import Dict, List

import ray

from featurizer.data_ingest.models import InputItemBatch
from featurizer.data_definitions.common.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.sql.client import FeaturizerSqlClient
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.feature_block_metadata import FeatureBlockMetadata

DB_ACTOR_NAME = 'DbActor'
DB_ACTOR_NAMESPACE = 'db'

# @ray.remote(resources={'worker_size_small': 1, 'instance_on_demand': 1})
@ray.remote
class DbActor:
    def __init__(self):
        self.client = FeaturizerSqlClient()

    async def filter_input_batch(self, input_batch: InputItemBatch) -> InputItemBatch:
        items = input_batch.items
        if len(items) == 0:
            return input_batch
        data_source_definition = items[0]['data_source_definition']
        if data_source_definition == CryptotickL2BookIncrementalData.__name__:
            return self.client.filter_cryptotick_batch(input_batch)
        else:
            raise ValueError(f'Unsupported data_source_definition: {data_source_definition}')

    async def store_block_metadata_batch(self, batch: List[DataSourceBlockMetadata | FeatureBlockMetadata]) -> Dict:
        # TODO check if exists
        self.client.store_block_metadata_batch(batch)
        # TODO return status to pass to stats actor
        return {}

    async def store_metadata(self, items: List[DataSourceBlockMetadata | FeatureBlockMetadata]) -> int:
        return self.client.store_metadata_if_needed(items)

    async def feature_block_exists(self, item: FeatureBlockMetadata) -> bool:
        return self.client.feature_block_exists(item)


def get_db_actor() -> ray.actor.ActorHandle:
    return ray.get_actor(name=DB_ACTOR_NAME, namespace=DB_ACTOR_NAMESPACE)


def create_db_actor() -> ray.actor.ActorHandle:
    return DbActor.options(name=DB_ACTOR_NAME, namespace=DB_ACTOR_NAMESPACE, lifetime='detached', get_if_exists=True).remote()

