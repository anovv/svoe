import featurizer.features.loader.df_utils as dfu
import featurizer.features.loader.l2_snapshot_utils as l2u
import featurizer.features.loader.catalog as catalog
import dask
import dask.dataframe

CHUNK_SIZE = 4  # how many files include in a chunk. Each chunk is an independent dask delayed object


# loads data from s3, takes care of partitioning for dask dataframes based on data_type
# i.e. l2_book deltas need to be partitioned so that each partition contains full book state
class Loader:
    def __init__(self):

        # TODO is this needed
        self.dask_cluster = None

    # TODO handle data versioning
    def l2_full(self, exchange, instrument_type, symbol, start=None, end=None):
        filenames_groups, has_overlap = catalog.get_filenames_groups('l2_book', exchange, instrument_type, symbol, start, end)
        # TODO what to do if has_overlap True? Indicate at least?
        chunked_filenames_groups = []
        for filenames_group in filenames_groups:
            chunked_filenames_groups.append([filenames_group[i:i + CHUNK_SIZE] for i in range(0, len(filenames_group), CHUNK_SIZE)])
        delayed_loaders = []
        for chunked_filenames in chunked_filenames_groups:
            for chunk_index in range(0, len(chunked_filenames)):
                delayed_loaders.append(
                    dask.delayed(self._load_and_repartition)(chunk_index, chunked_filenames)
                )

        return dask.dataframe.from_delayed(delayed_loaders)

    def _load_chunk(self, chunk_index, chunked_filenames):
        return dfu._load_df(chunked_filenames[chunk_index], CHUNK_SIZE)

    def _load_and_repartition(self, chunk_index, chunked_filenames):
        # load current chunk, load previous/next chunk if needed until full snapshot is restored
        current = self._load_chunk(chunk_index, chunked_filenames)
        prev_index = chunk_index - 1
        next_index = chunk_index + 1
        if not l2u._has_snapshot(current):
            # this will be handled by previous chunk
            return None  # TODO make empty df

        if l2u._starts_with_snapshot(current) and prev_index >= 0:
            # load previous in case it has leftover snapshot data
            previous = self._load_chunk(prev_index, chunked_filenames)
            if l2u._ends_with_snapshot(previous):
                # append previous snapshot data to current head
                prev_end = previous.iloc[-1].name
                prev_last_snapshot_start = l2u._get_snapshot_start(previous, prev_end)
                prev_snapshot = dfu._sub_df(previous, prev_last_snapshot_start, prev_end)
                current = dfu._concat([prev_snapshot, current])

        next = None
        if l2u._ends_with_snapshot(current) and next_index < len(chunked_filenames):
            # to make things even, remove end snapshot from current if it will be handled by next partition
            next = self._load_chunk(next_index, chunked_filenames)
            if l2u._starts_with_snapshot(next):
                # remove cur snapshot data from end
                cur_end = current.iloc[-1].name
                cur_last_snapshot_start = l2u._get_snapshot_start(current, cur_end)
                current = dfu._sub_df(current, 0, cur_last_snapshot_start - 1)

        # append deltas to current until next snapshot is reached
        while next_index < len(chunked_filenames) and (next is None or not l2u._has_snapshot(next)):
            next = self._load_chunk(next_index, chunked_filenames)
            if not l2u._has_snapshot(next):
                current = dfu._concat([current, next])
            next_index += 1
        if next is not None and l2u._has_snapshot(next):
            next_first_snap_start = l2u._get_first_snapshot_start(next)
            next_deltas = dfu._sub_df(next, 0, next_first_snap_start - 1)
            current = dfu._concat([current, next_deltas])

        # remove all deltas from beginning to make sure we start with snapshot data
        current_first_snap_start = l2u._get_first_snapshot_start(current)
        current = dfu._sub_df(current, current_first_snap_start, current.iloc[-1].name)

        return current
