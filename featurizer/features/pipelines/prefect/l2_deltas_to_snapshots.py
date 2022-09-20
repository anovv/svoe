
from prefect import task, flow, unmapped
import featurizer.features.loader.loader as loader
import featurizer.features.loader.catalog as catalog
import time

CHUNK_SIZE = 10

def get_compaction_groups(dfs):
    return []


@task
def load_grouped_filenames_chunks(exchange, instrument_type, symbol):
    filenames_groups, has_overlap = catalog.get_filenames_groups('l2_book', exchange, instrument_type, symbol)
    chunked_grouped = catalog.chunk_filenames_groups(filenames_groups, CHUNK_SIZE)
    return chunked_grouped

@task
def load_l2_deltas_chunk(index, chunks):
    return loader.load_with_snapshot(index, chunks, CHUNK_SIZE)

@task
def transform_deltas_chunk_to_full(deltas_chunk_df):
    # TODO
    time.sleep(1)
    return deltas_chunk_df

@task
def compact_and_store(dfs):
    #concatinate dataframes into one and store to data lake
    # use data wrangler
    # update index
    # TODO
    time.sleep(1)
    return

@flow
def l2_deltas_to_snapshots_flow(exchange, instrument_type, symbol):
    grouped_chunks = load_grouped_filenames_chunks(exchange, instrument_type, symbol)
    chunks = [chunk for group in grouped_chunks for chunk in group] # flatten

    # map loaders
    mapped_loaders = load_l2_deltas_chunk.map(range(len(chunks)), chunks=unmapped(chunks))

    # group into compaction groups


    return
