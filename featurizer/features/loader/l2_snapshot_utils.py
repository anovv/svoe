
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