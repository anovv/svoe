from ray import workflow

from featurizer.data_catalog.common.actors.db import DbActor
from featurizer.data_catalog.common.data_models.models import InputItemBatch
from featurizer.data_catalog.common.tasks.tasks_DEPRECATED import filter_existing, load_df, catalog_df, gather_and_wait, write_batch, chain_no_ret
from featurizer.data_catalog.common.utils.register import ray_task_name, EventType, send_events_to_stats
from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.data_catalog import Dag


class CatalogCryptofeedDag(Dag):

    def get(self, dag_id: str, input_batch: InputItemBatch, db_actor: DbActor):
        stats = None # TODO we deprecate/upgrade Stats actor
        filter_task_id = f'{dag_id}_{ray_task_name(filter_existing)}'

        # construct DAG
        _, filtered_items = workflow.continuation(
            filter_existing.options(**workflow.options(task_id=filter_task_id), num_cpus=0.01).bind(
                db_actor, input_batch, stats=stats, task_id=filter_task_id
            ))

        download_task_ids = []
        catalog_task_ids = []
        stats_extras = []
        catalog_tasks = []

        for i in range(len(filtered_items)):
            item = filtered_items[i]
            stats_extra = {'size_kb': item['size_kb']}
            stats_extras.append(stats_extra)

            download_task_id = f'{dag_id}_{ray_task_name(load_df)}_{i}'
            download_task_ids.append(download_task_id)
            download_task = load_df.options(**workflow.options(task_id=download_task_id), num_cpus=0.001).bind(
                item, stats=stats, task_id=download_task_id, stats_extra=stats_extra
            )
            catalog_task_id = f'{dag_id}_{ray_task_name(catalog_df)}_{i}'
            catalog_task_ids.append(catalog_task_id)
            item[DataCatalog.source.name] = 'cryptofeed'
            catalog_task = catalog_df.options(**workflow.options(task_id=catalog_task_id), num_cpus=0.9).bind(
                download_task, item, stats=stats, task_id=catalog_task_id
            )
            catalog_tasks.append(catalog_task)

        # report scheduled events to stats
        scheduled_events_reported = gather_and_wait.bind([
            send_events_to_stats.bind(stats, download_task_ids, ray_task_name(load_df), EventType.SCHEDULED, stats_extras),
            send_events_to_stats.bind(stats, catalog_task_ids, ray_task_name(catalog_df), EventType.SCHEDULED, stats_extras)
        ])

        # bind stats sched report
        gathered_catalog_items = gather_and_wait.bind(catalog_tasks)
        node = chain_no_ret.bind(gathered_catalog_items, scheduled_events_reported)

        write_task_id = f'{dag_id}_{ray_task_name(write_batch)}'
        dag = write_batch.options(**workflow.options(task_id=write_task_id), num_cpus=0.01).bind(
            db_actor, node, stats=stats, task_id=write_task_id
        )

        return dag