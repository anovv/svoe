from data_eng.athena import get_s3_filenames
import awswrangler as wr
import pandas as pd


# loads data from s3, takes care of partitioning for dask dataframes based on data_type
# i.e. l2_book deltas need to be partitioned so that each partition contains full book state
class Loader:
    def __init__(self):
        self.dask_cluster = None

    # TODO handle data versioning
    def l2_full(self, exchange, instrument_type, symbol, start, end):
        # TODO are these sorted
        filenames = get_s3_filenames('l2_book', exchange, instrument_type, symbol, start, end)
        CHUNK_SIZE = 4  # how many files include in a chunk. Each chunk is an independent dask delayed object
        chunked = [filenames[i:i + CHUNK_SIZE] for i in range(0, len(filenames), CHUNK_SIZE)]

        def _load_chunk(chunk_index):
            return wr.s3.read_parquet(path=chunked[chunk_index], use_threads=CHUNK_SIZE)

        def _starts_with_snapshot(df):
            return df.iloc[0].delta == False

        def _ends_with_snapshot(df):
            return df.iloc[-1].delta == False

        def _has_snapshot(df):
            return False in df.delta.values

        def _get_first_snapshot_start(df):
            return df[df.delta == False].iloc[0].name

        # def _get_snapshot_end(df, start):
        #     return 0 # TODO

        def _get_snapshot_start(df, end):
            cur = end - 1
            while cur >= 0 and df.iloc[cur].delta == False:
                cur -= 1
            return cur + 1

        def _sub_df(df, start, end):
            # includes end
            return df[start: end + 1]

        def _concat(df1, df2):
            return pd.concat([df1, df2], ignore_index=True)

        def _load_and_repartition(chunk_index):
            # load current chunk, load previous/next chunk if needed until full snapshot is restored
            current = _load_chunk(chunk_index)
            prev_index = chunk_index - 1
            next_index = chunk_index + 1
            if not _has_snapshot(current):
                # this will be handled by previous chunk
                return None # TODO make empty df

            if _starts_with_snapshot(current) and prev_index >= 0:
                # load previous in case it has leftover snapshot data
                previous = _load_chunk(prev_index)
                if _ends_with_snapshot(previous):
                    # append previous snapshot data to current head
                    prev_end = previous.iloc[-1].name
                    prev_last_snapshot_start = _get_snapshot_start(previous, prev_end)
                    prev_snapshot = _sub_df(previous, prev_last_snapshot_start, prev_end)
                    current = _concat(prev_snapshot, current)

            next = None
            if _ends_with_snapshot(current) and next_index < len(chunked):
                # to make things even, remove end snapshot from current if it will be handled by next partition
                next = _load_chunk(next_index)
                if _starts_with_snapshot(next):
                    # remove cur snapshot data from end
                    cur_end = current.iloc[-1].name
                    cur_last_snapshot_start = _get_snapshot_start(current, cur_end)
                    current = _sub_df(current, 0, cur_last_snapshot_start - 1)

            # append deltas to current until next snapshot is reached
            while next_index < len(chunked) and (next is None or not _has_snapshot(next)):
                next = _load_chunk(next_index)
                if not _has_snapshot(next):
                    current = _concat(current, next)
                next_index += 1
            if _has_snapshot(next):
                next_first_snap_start = _get_first_snapshot_start(next)
                next_deltas = _sub_df(next, 0, next_first_snap_start - 1)
                current = _concat(current, next_deltas)

            # remove all deltas from beginning to make sure we start with snapshot data
            current_first_snap_start = _get_first_snapshot_start(current)
            current = _sub_df(current, current_first_snap_start, current.iloc[-1].name)

            return current
