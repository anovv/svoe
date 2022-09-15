
def _starts_with_snapshot(df):
    return df.iloc[0].delta == False


def _ends_with_snapshot(df):
    return df.iloc[-1].delta == False


def _has_snapshot(df):
    return False in df.delta.values


def _get_first_snapshot_start(df):
    return df[df.delta == False].iloc[0].name


def _get_snapshot_start(df, end):
    for r in _get_snapshots_ranges(df):
        if r[1] == end:
            return r[0]
    return -1


def _get_snapshots_ranges(df):
    # https://stackoverflow.com/questions/60092544/how-to-get-start-and-end-index-of-group-of-1s-in-a-series
    df = df.reset_index()
    snapshot_rows = df['delta'].astype(int).eq(0)
    grouper = snapshot_rows.ne(snapshot_rows.shift()).cumsum()[snapshot_rows]
    snapshot_ranges_df = df.groupby(grouper)['index'].agg([('start', 'first'), ('end', 'last')]).reset_index(drop=True)

    return list(snapshot_ranges_df.itertuples(index=False, name=None))





