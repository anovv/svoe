from ray import workflow

from data_catalog.common.actors.db import DbActor
from data_catalog.common.actors.stats import Stats
from data_catalog.common.data_models.models import InputItemBatch
from data_catalog.common.tasks.tasks import filter_existing, load_df, index_df, gather_and_wait, gather_and_wait_empty_return, write_batch
from data_catalog.common.utils.register import ray_task_name, send_events_to_stats, EventType


def build_index_cryptofeed_dag(workflow_id: str, input_batch: InputItemBatch, stats: Stats, db_actor: DbActor):
    filter_task_id = f'{workflow_id}_{ray_task_name(filter_existing)}'
    # construct DAG


    _, filtered_items = workflow.continuation(
        filter_existing.options(**workflow.options(task_id=filter_task_id), num_cpus=0.01).bind(db_actor,
                                                                                                input_batch,
                                                                                                stats=stats,
                                                                                                task_id=filter_task_id))

    download_task_ids = []
    index_task_ids = []
    extras = []
    index_tasks = []

    for i in range(len(filtered_items)):
        item = filtered_items[i]
        download_task_ids.append(f'{workflow_id}_{ray_task_name(load_df)}_{i}')
        index_task_ids.append(f'{workflow_id}_{ray_task_name(index_df)}_{i}')
        extras.append({'size_kb': item['size_kb']})

    # report scheduled events to stats
    scheduled_events_reported = gather_and_wait_empty_return.bind([
        send_events_to_stats.bind(stats, download_task_ids, ray_task_name(load_df), EventType.SCHEDULED, extras),
        send_events_to_stats.bind(stats, index_task_ids, ray_task_name(index_df), EventType.SCHEDULED, extras)
    ])

    for i in range(len(filtered_items)):
        download_task_id = download_task_ids[i]
        download_task = load_df.options(**workflow.options(task_id=download_task_id), num_cpus=0.001).bind(item,
                                                                                                           stats=stats,
                                                                                                           task_id=download_task_id,
                                                                                                           extra=extras[i])
        index_task_id = index_task_ids[i]
        index_task = index_df.options(**workflow.options(task_id=index_task_id), num_cpus=0.01).bind(download_task,
                                                                                                     item,
                                                                                                     stats=stats,
                                                                                                     task_id=index_task_id,
                                                                                                     extra=extras[i])
        index_tasks.append(index_task)

    # scheduled_events_reported is empty, used for synchronous wait
    upstream = index_tasks.extend(scheduled_events_reported)
    gathered_index_items = gather_and_wait.bind(upstream)

    write_task_id = f'{workflow_id}_{ray_task_name(write_batch)}'
    dag = write_batch.options(**workflow.options(task_id=write_task_id), num_cpus=0.01).bind(db_actor,
                                                                                             gathered_index_items,
                                                                                             stats=stats,
                                                                                             task_id=write_task_id)

    # scheduled_events = []
    # now = time.time()
    # for _id in download_task_ids:
    #     scheduled_events.append({
    #         'task_id': _id,
    #         'event_name': get_event_name(ray_task_name(load_df), EventType.SCHEDULED),
    #         'timestamp': now
    #     })
    # self.stats.events.remote(ray_task_name(load_df), scheduled_events)
    # scheduled_events = []
    # now = time.time()
    # for _id in index_task_ids:
    #     scheduled_events.append({
    #         'task_id': _id,
    #         'event_name': get_event_name(ray_task_name(index_df), EventType.SCHEDULED),
    #         'timestamp': now
    #     })
    # self.stats.events.remote(ray_task_name(index_df), scheduled_events)
    return dag