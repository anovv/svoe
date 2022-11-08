import pandas as pd
import featurizer.features.loader.df_utils as dfu
from typing import List, Tuple, Dict, Any
from featurizer.features.definitions.data_models_utils import L2BookDelta
from collections import OrderedDict
from tqdm import tqdm


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


def get_info(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        'df_size_kb': dfu.get_size_kb(df),
        'length': dfu.get_len(df),
        'starts_with_snapshot': starts_with_snapshot(df),
        'ends_with_snapshot': ends_with_snapshot(df),
        'has_snapshot': has_snapshot(df),
        'snapshot_ranges': get_snapshots_ranges(df)
    }


def parse_l2_book_delta_events(deltas: pd.DataFrame) -> List[L2BookDelta]:
    # parses dataframe into list of events
    grouped = deltas.groupby(['timestamp', 'delta'])
    dfs = [grouped.get_group(x) for x in grouped.groups]
    dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
    events = []
    for i in tqdm(range(len(dfs))):
        df = dfs[i]
        timestamp = df.iloc[0].timestamp
        receipt_timestamp = df.iloc[0].receipt_timestamp
        delta = df.iloc[0].delta
        orders = []
        #TODO https://stackoverflow.com/questions/7837722/what-is-the-most-efficient-way-to-loop-through-dataframes-with-pandas
        # regarding iteration speed
        # TODO use numba's jit
        df_dict = df.to_dict(into=OrderedDict, orient='index') # TODO use df.values.tolist() instead and check perf?
        for v in df_dict.values():
            orders.append((v['side'], v['price'], v['size']))
        events.append(L2BookDelta(
            timestamp=timestamp,
            receipt_timestamp=receipt_timestamp,
            delta=delta,
            orders=orders
        ))

        return events





