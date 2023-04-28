from ray import workflow

from data_catalog.common.actors.db import DbActor
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.tasks.tasks import gather_and_wait, chain_no_ret, store_df, filter_existing, write_batch
from data_catalog.common.utils.sql.models import DataCatalog
from data_catalog.pipelines.catalog_cryptotick.tasks import load_split_catalog_l2_inc_df
from data_catalog.pipelines.dag import Dag

SPLIT_CHUNK_SIZE_KB = 100 * 1024


class CatalogCryptotickDag(Dag):

    def get(self, dag_id: str, input_batch: InputItemBatch, db_actor: DbActor):
        # filter_task_id = f'{dag_id}_{ray_task_name(filter_existing)}'

        _, filtered_items = workflow.continuation(filter_existing.options(num_cpus=0.01).bind(
            db_actor, input_batch
        ))

        dag_nodes = []

        for i in range(len(filtered_items)):
            item = filtered_items[i]
            # raw_size_kb = item[DataCatalog.size_kb.name]
            # stats_extra = {'size_kb': raw_size_kb} # TODO report load size for throughput

            # load_split_catalog_task_id = f'{dag_id}_{ray_task_name(load_split_catalog_l2_inc_df)}_{i}'
            load_split_catalog_task = load_split_catalog_l2_inc_df.options(num_cpus=0.001, resources={'worker_size_large': 1, 'instance_spot': 1}).bind(
                item, SPLIT_CHUNK_SIZE_KB, item['date']
            )
            splits, catalog_items = workflow.continuation(load_split_catalog_task)
            store_tasks = []
            for j in range(len(splits)):

                store_task = store_df.options(num_cpus=0.01, resources={'worker_size_large': 1, 'instance_spot': 1}).bind(
                    splits[j], catalog_items[j]
                )
                store_tasks.append(store_task)

            write_db_task = write_batch.options(num_cpus=0.01, resources={'worker_size_large': 1, 'instance_spot': 1}).bind(
                db_actor, catalog_items
            )

            dag_nodes.append(chain_no_ret.options(resources={'worker_size_large': 1, 'instance_spot': 1}).bind(
                write_db_task, store_tasks
            ))

        return gather_and_wait.options(resources={'worker_size_large': 1, 'instance_spot': 1}).bind(dag_nodes)
