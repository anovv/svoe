
from prefect import task, flow, unmapped
import featurizer.features.loader.loader as loader
import featurizer.features.loader.catalog as catalog
import time

CHUNK_SIZE = 10 # number of files to treat as a single chunk/dataframe
COMPACTION_GROUP_SIZE = 20 # number of chunks to store in the same file


def get_compaction_groups(grouped_chunks, compaction_group_size):
    # TODO move this to utility class?
    # we need to make sure not to compact together chunks from different groups
    #[[[a, b, c], [d, e], [f, g]], [[h, k], [l, n]], [[n, o], [p, q, r], [s, t]]]
    id = 0
    grouped_chunk_ids = []
    for group in grouped_chunks:
        grouped_ids = []
        for chunk in group:
            grouped_ids.append(id)
            id += 1
        grouped_chunk_ids.append(grouped_ids)
    # [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10]]
    compaction_groups = []
    for grouped_ids in grouped_chunk_ids:
        compacted_ids = [grouped_ids[i:i + compaction_group_size] for i in range(0, len(grouped_ids), compaction_group_size)]
        compaction_groups.extend(compacted_ids)
    return compaction_groups

@task
def load_grouped_filenames_chunks(exchange, instrument_type, symbol):
    filenames_groups, has_overlap = catalog.get_filenames_groups('l2_book', exchange, instrument_type, symbol)
    grouped_chunks = catalog.chunk_filenames_groups(filenames_groups, CHUNK_SIZE)
    return grouped_chunks

@task
def load_l2_deltas_chunk(index, chunks):
    return loader.load_with_snapshot(index, chunks, CHUNK_SIZE)

@task
def transform_deltas_to_snapshots(deltas_df):
    # TODO
    time.sleep(1)
    return deltas_df

@task
def compact_and_store(ids, dfs):
    #concatinate dataframes into one and store to data lake
    # use data wrangler
    # update index
    # TODO
    time.sleep(1)
    return None

@task
def gather_results(results):
    # TODO
    # gather pipeline stats
    time.sleep(1)
    return True

@flow
def l2_deltas_to_snapshots_flow(exchange, instrument_type, symbol):
    grouped_chunks = load_grouped_filenames_chunks(exchange, instrument_type, symbol)
    chunks = [chunk for group in grouped_chunks for chunk in group] # flatten

    # map loaders
    mapped_loaders = load_l2_deltas_chunk.map(range(len(chunks)), chunks=unmapped(chunks))

    # transform deltas to snaps
    mapped_transform = transform_deltas_to_snapshots.map(mapped_loaders)

    # make compaction groups
    compaction_groups = get_compaction_groups(grouped_chunks)

    # store
    results = compact_and_store.map(compaction_groups, dfs=unmapped(mapped_transform))

    # gather stats
    stats = gather_results(results)

    return stats
