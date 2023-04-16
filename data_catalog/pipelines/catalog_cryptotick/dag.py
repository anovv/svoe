from ray import workflow

from data_catalog.common.actors.db import DbActor
from data_catalog.common.actors.stats import Stats
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.tasks.tasks import gather_and_wait, load_df, catalog_df, chain_no_ret, \
    write_batch, store_df, split_l2_inc_df, filter_existing
from data_catalog.common.utils.register import ray_task_name, send_events_to_stats, EventType
from data_catalog.common.utils.sql.models import DataCatalog
from data_catalog.pipelines.dag import Dag

SPLIT_CHUNK_SIZE_KB = 1024


class CatalogCryptotickDag(Dag):

    def get(self, dag_id: str, input_batch: InputItemBatch, stats: Stats, db_actor: DbActor):
        filter_task_id = f'{dag_id}_{ray_task_name(filter_existing)}'

        _, filtered_items = workflow.continuation(
            filter_existing.options(**workflow.options(task_id=filter_task_id), num_cpus=0.01).bind(
                db_actor, input_batch, stats=stats, task_id=filter_task_id
            ))

        download_task_ids = []
        catalog_task_ids = []
        store_task_ids = []
        stats_extras = []
        store_tasks = []
        catalog_tasks = []

        for i in range(len(filtered_items)):
            item = filtered_items[i]
            raw_size_kb = item[DataCatalog.size_kb.name]
            stats_extra = {'size_kb': raw_size_kb}
            stats_extras.append(stats_extra)

            download_task_id = f'{dag_id}_{ray_task_name(load_df)}_{i}'
            download_task_ids.append(download_task_id)
            download_task = load_df.options(**workflow.options(task_id=download_task_id), num_cpus=0.001).bind(
                item, stats=stats, task_id=download_task_id, stats_extra=stats_extra
            )

            split_task_id = f'{dag_id}_{ray_task_name(split_l2_inc_df)}_{i}'
            splits = workflow.continuation(split_l2_inc_df.options(**workflow.options(task_id=split_task_id), num_cpus=0.9).bind(
                download_task, SPLIT_CHUNK_SIZE_KB, item['date'], stats=stats, task_id=split_task_id
            ))

            for j in range(len(splits)):
                split = splits[j]
                item_split = item.copy()

                # additional info to be passed to catalog item
                compaction = f'{SPLIT_CHUNK_SIZE_KB}kb' if SPLIT_CHUNK_SIZE_KB < 1024 else f'{round(SPLIT_CHUNK_SIZE_KB / 1024, 2)}mb'
                item_split[DataCatalog.compaction.name] = compaction
                item_split[DataCatalog.source.name] = 'cryptotick'
                item_split[DataCatalog.extras.name] = {
                    'source_path': item_split[DataCatalog.path.name],
                    'split_id': j,
                    'num_splits': len(splits),
                }

                # remove raw source path so it is constructed when making catalog item
                del item_split[DataCatalog.path.name]

                catalog_task_id = f'{dag_id}_{ray_task_name(catalog_df)}_{j}_{i}'
                catalog_task_ids.append(catalog_task_id)

                catalog_task = catalog_df.options(**workflow.options(task_id=catalog_task_id), num_cpus=0.9).bind(
                    split, item_split, stats=stats, task_id=catalog_task_id
                )
                catalog_tasks.append(catalog_task)

                store_task_id = f'{dag_id}_{ray_task_name(store_df)}_{j}_{i}'
                store_task_ids.append(store_task_id)
                store_task = store_df.options(**workflow.options(task_id=store_task_id), num_cpus=0.01).bind(
                    split, catalog_task, stats=stats, task_id=store_task_id, stats_extra={'size_kb': raw_size_kb/len(splits)}
                )
                store_tasks.append(store_task)

        # report scheduled events to stats
        scheduled_events_reported = gather_and_wait.bind([
            send_events_to_stats.bind(stats, download_task_ids, ray_task_name(load_df), EventType.SCHEDULED, stats_extras),
        ])

        gathered_store_tasks = gather_and_wait.bind(store_tasks)
        gathered_catalog_tasks = gather_and_wait.bind(catalog_tasks)
        # TODO verify all is stored successfully here?
        gathered_catalog_tasks = chain_no_ret.bind(gathered_catalog_tasks, gathered_store_tasks, scheduled_events_reported)

        write_catalog_task_id = f'{dag_id}_{ray_task_name(write_batch)}'
        dag = write_batch.options(**workflow.options(task_id=write_catalog_task_id), num_cpus=0.01).bind(
            db_actor, gathered_catalog_tasks, stats=stats, task_id=write_catalog_task_id
        )

        return dag
