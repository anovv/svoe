import featurizer.features.loader.df_utils as dfu
import featurizer.features.loader.l2_snapshot_utils as l2u
import featurizer.features.loader.catalog as catalog
import concurrent.futures
import asyncio
import functools


def test_load_and_repartition(self):
    filenames_groups, has_overlap = catalog.get_filenames_groups('l2_book', 'BINANCE', 'spot', 'BTC-USDT')
    filenames = []
    for group in filenames_groups:
        filenames.extend(group)

    filenames = filenames[0:50]

    df1 = dfu._concat(dfu._load_dfs_concurrent(filenames))
    df2 = dfu._concat(self._load_and_repartition_concurrently(filenames))
    r1 = l2u._get_snapshots_ranges(df1)
    r2 = l2u._get_snapshots_ranges(df2)
    assert r1 == r2


def _load_and_repartition_concurrently(self, chunked_filenames):
    # this is used only for testing
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1024)
    loop = asyncio.new_event_loop()
    futures = [
        loop.run_in_executor(
            executor,
            functools.partial(self._load_and_repartition, chunk_index=i, chunked_filenames=chunked_filenames)
        )
        for i in range(0, len(chunked_filenames))
    ]
    gathered = asyncio.gather(*futures, loop=loop, return_exceptions=True)
    loop.run_until_complete(gathered)
    dfs = []
    for f in futures:
        dfs.append(f.result())
    return dfs