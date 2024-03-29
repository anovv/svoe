import pandas as pd
from typing import List, Tuple, Optional


def starts_with_snapshot(df: pd.DataFrame) -> bool:
    if len(df) == 0:
        return False
    return df.iloc[0].delta == False


def ends_with_snapshot(df: pd.DataFrame) -> bool:
    if len(df) == 0:
        return False
    return df.iloc[-1].delta == False


def has_snapshot(df: pd.DataFrame) -> bool:
    if len(df) == 0:
        return False
    return False in df.delta.values


def get_first_snapshot_start(df: pd.DataFrame) -> int:
    if len(df) == 0:
        return -1
    return df[df.delta == False].iloc[0].name


def get_snapshot_start(df: pd.DataFrame, end: int) -> int:
    if len(df) == 0:
        return -1
    for r in get_snapshots_ranges(df):
        if r[1] == end:
            return r[0]
    return -1


def get_snapshots_ranges(df: pd.DataFrame) -> List[Tuple[int, int]]:
    if len(df) == 0:
        return []
    # https://stackoverflow.com/questions/60092544/how-to-get-start-and-end-index-of-group-of-1s-in-a-series
    df = df.reset_index()
    snapshot_rows = df['delta'].astype(int).eq(0)
    grouper = snapshot_rows.ne(snapshot_rows.shift()).cumsum()[snapshot_rows]
    snapshot_ranges_df = df.groupby(grouper)['index'].agg([('start', 'first'), ('end', 'last')]).reset_index(drop=True)

    return list(snapshot_ranges_df.itertuples(index=False, name=None))


def get_snapshot_ts(df: pd.DataFrame) -> Optional[List]:
    snaps = df[df.delta == False]
    if len(snaps) == 0:
        return None
    return list(snaps.timestamp.unique())
