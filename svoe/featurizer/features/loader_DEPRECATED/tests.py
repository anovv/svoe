import svoe.common.pandas.df_utils as dfu
from svoe import featurizer as l2u
import svoe.featurizer.features.loader_DEPRECATED.catalog as catalog
import svoe.common.concurrency.concurrency_utils as cu
import svoe.featurizer.features.loader_DEPRECATED.loader as loader
import functools
import pandas as pd

from typing import List


def test_load_and_repartition():
    filenames_groups, has_overlap = catalog.get_filenames_groups('l2_book', 'BINANCE', 'spot', 'BTC-USDT')

    # limit for testing
    filenames_groups = filenames_groups[0:10]

    filenames = []
    for group in filenames_groups:
        filenames.extend(group)

    df1 = dfu.concat(dfu.load_files(filenames))
    df2 = dfu.concat(_load_and_repartition_concurrently(filenames_groups))
    r1 = l2u.get_snapshots_ranges(df1)
    r2 = l2u.get_snapshots_ranges(df2)
    assert r1 == r2


def _load_and_repartition_concurrently(chunked_filenames: List[List[str]]) -> List[pd.DataFrame]:
    callables = [
        functools.partial(loader.load_with_snapshot, chunk_index=i, chunked_filenames=chunked_filenames)
        for i in range(0, len(chunked_filenames))
    ]
    return cu.run_concurrently(callables)
