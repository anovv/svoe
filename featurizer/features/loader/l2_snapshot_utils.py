
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


def _get_snapshots_ranges(df):
    # https://towardsdatascience.com/400x-time-faster-pandas-data-frame-iteration-16fb47871a0a
    # returns start and end indices of all snapshots
    ranges = []
    cur_start = None
    index = 0
    in_snapshot = False
    # TODO use to_dict to iterate over dict for a speedup
    for _, row in df.iterrows():
        if row.delta == True:
            if cur_start is not None and in_snapshot:
                # cur snap finished
                cur_end = index - 1
                in_snapshot = False
                # save cur snap
                if cur_start is not None:
                    ranges.append((cur_start, cur_end))
        else:
            if not in_snapshot:
                # new snap found
                cur_start = index
                in_snapshot = True
        index += 1

    return ranges



