from typing import Optional, List

import pandas as pd


def get_snapshot_ts(df: pd.DataFrame) -> Optional[List]:
    snaps = df[df.update_type == 'SNAPSHOT']
    if len(snaps) == 0:
        return None
    return list(snaps.time_exchange.unique())


def starts_with_snapshot(df: pd.DataFrame) -> bool:
    if len(df) == 0:
        return False
    return df.iloc[0]['update_type'] == 'SNAPSHOT'

def remove_snap(df: pd.DataFrame) -> pd.DataFrame:
    # TODO
    return df

def get_snapshot_depth(df: pd.DataFrame) -> int:
    # TODO
    return 0