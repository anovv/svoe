import utils.pandas.df_utils as dfu
import featurizer.features.data.l2_book_incremental.cryptofeed.l2_snapshot_utils as l2u
import featurizer.features.loader.catalog as catalog
import pandas as pd
import dask
import dask.dataframe as dd
from typing import List

CHUNK_SIZE = 100  # how many files include in a chunk. Each chunk is an independent dask delayed object


# loads data from s3, takes care of partitioning for dask dataframes based on data_type
# i.e. l2_book deltas need to be partitioned so that each partition contains full book state

# TODO handle data versioning
def l2_deltas_dask_dataframe(
    exchange: str,
    instrument_type: str,
    symbol: str,
    start: str = None,
    end: str = None
) -> dd.DataFrame:
    filenames_groups, has_overlap = catalog.get_filenames_groups('l2_book', exchange, instrument_type, symbol,
                                                                 start, end)
    # TODO what to do if has_overlap True? Indicate at least?

    chunked_filenames_groups = catalog.chunk_filenames_groups(filenames_groups, CHUNK_SIZE)
    delayed_loaders = []
    for chunked_filenames in chunked_filenames_groups:
        for chunk_index in range(0, len(chunked_filenames)):
            delayed_loaders.append(
                dask.delayed(load_with_snapshot)(chunk_index, chunked_filenames, CHUNK_SIZE)
            )

    return dd.from_delayed(delayed_loaders)


def load_chunk(chunk_index: int, chunked_filenames: List[List[str]]) -> pd.DataFrame:
    return dfu.concat(dfu.load_files(chunked_filenames[chunk_index]))


def load_with_snapshot(chunk_index: int, chunked_filenames: List[List[str]]) -> pd.DataFrame:
    # load current chunk, load previous/next chunk if needed until full snapshot is restored
    current = load_chunk(chunk_index, chunked_filenames)
    prev_index = chunk_index - 1
    next_index = chunk_index + 1
    if not l2u.has_snapshot(current):
        # this will be handled by previous chunk, return empty df
        # TODO the df schema should be a global shared/common variable between this and data feed service
        return pd.DataFrame({
            'timestamp': pd.Series(dtype='float64'),
            'receipt_timestamp': pd.Series(dtype='float64'),
            'delta': pd.Series(dtype='boolean'),
            'side': pd.Series(dtype='string'),
            'price': pd.Series(dtype='float64'),
            'size': pd.Series(dtype='float64'),
            'exchange': pd.Series(dtype='category'),
            'instrument_type': pd.Series(dtype='category'),
            'instrument_extra': pd.Series(dtype='category'),
            'symbol': pd.Series(dtype='category'),
            'base': pd.Series(dtype='category'),
            'quote': pd.Series(dtype='category'),
            'date': pd.Series(dtype='category'),
            'compaction': pd.Series(dtype='category'),
            'version': pd.Series(dtype='category')
        })


    if l2u.starts_with_snapshot(current) and prev_index >= 0:
        # load previous in case it has leftover snapshot data
        previous = load_chunk(prev_index, chunked_filenames)
        if l2u.ends_with_snapshot(previous):
            # append previous snapshot data to current head
            prev_end = previous.iloc[-1].name
            prev_last_snapshot_start = l2u.get_snapshot_start(previous, prev_end)
            prev_snapshot = dfu.sub_df(previous, prev_last_snapshot_start, prev_end)
            current = dfu.concat([prev_snapshot, current])

    next = None
    if l2u.ends_with_snapshot(current) and next_index < len(chunked_filenames):
        # to make things even, remove end snapshot from current if it will be handled by next partition
        next = load_chunk(next_index, chunked_filenames)
        if l2u.starts_with_snapshot(next):
            # remove cur snapshot data from end
            cur_end = current.iloc[-1].name
            cur_last_snapshot_start = l2u.get_snapshot_start(current, cur_end)
            current = dfu.sub_df(current, 0, cur_last_snapshot_start - 1)

    # append deltas to current until next snapshot is reached
    while next_index < len(chunked_filenames) and (next is None or not l2u.has_snapshot(next)):
        next = load_chunk(next_index, chunked_filenames)
        if not l2u.has_snapshot(next):
            current = dfu.concat([current, next])
        next_index += 1
    if next is not None and l2u.has_snapshot(next):
        next_first_snap_start = l2u.get_first_snapshot_start(next)
        next_deltas = dfu.sub_df(next, 0, next_first_snap_start - 1)
        current = dfu.concat([current, next_deltas])

    # remove all deltas from beginning to make sure we start with snapshot data
    current_first_snap_start = l2u.get_first_snapshot_start(current)
    current = dfu.sub_df(current, current_first_snap_start, current.iloc[-1].name)

    return current
