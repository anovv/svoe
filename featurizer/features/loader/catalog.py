# contains functions abstracting index/catalog queries

import awswrangler as wr
import intervaltree as it
import matplotlib.pyplot as plt

DATABASE = 'svoe_glue_db'
GROUP_TIME_DIFF_S = 10 # if intervals difference is less than this, they are grouped

# TODO use max_cache_seconds
# https://ahana.io/answers/how-do-i-get-the-date_diff-from-previous-rows/
# To cast to timestamp
# select distinct from_unixtime(timestamp) from l2_book where exchange='BINANCE' and instrument_type='spot' and symbol='BTC-USDT' and date='2022-07-13'

# to get ts diffs
# select ts, date_diff('millisecond', ts, lag(ts) over(order by ts desc)) as diff from (
#     select distinct from_unixtime(timestamp) as ts from ticker where exchange='BINANCE' and instrument_type='spot' and symbol='BTC-USDT' and date='2022-07-13')

# missing ranges by symbol
# select prev, ts, symbol from
# (
#     select ts, prev, date_diff('millisecond', prev, ts) as diff_prev, symbol from
#     (
#         select ts, lag(ts) over(partition by symbol order by ts asc) as prev, symbol from
#         (
#             select distinct from_unixtime(timestamp) as ts, symbol from l2_book where exchange='BINANCE' and instrument_type='spot'
#         )
#     )
# )
# where diff_prev > 60 * 1000


def get_available_dates(channel, exchange, instrument_type, symbol):
    df = wr.athena.read_sql_query(
        sql='SELECT DISTINCT date FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol;',
        database=DATABASE,
        params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'", 'symbol': f"'{symbol}'"},
        max_cache_seconds=900
    )

    return df['date'].to_list()


def get_sorted_filenames(channel, exchange, instrument_type, symbol, start_date=None, end_date=None, compaction='raw'):
    start_date, end_date = _sanitize_dates(start_date, end_date)
    df = wr.athena.read_sql_query(
        sql='SELECT DISTINCT "$path", version FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol; AND date >= :start; AND date <= :end; AND compaction=:compaction;',
        database=DATABASE,
        params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'", 'symbol': f"'{symbol}'", 'start': f"'{start_date}'", 'end': f"'{end_date}'", 'compaction':  f"'{compaction}'"},
        max_cache_seconds=900
    )

    filenames_per_version = df.groupby('version')['$path'].apply(list).to_dict()
    intervals_per_version = {
        version: list(map(lambda filename: _parse_interval(filename), filenames_per_version[version]))
        for version in filenames_per_version
    }

    # by default, if we have multiple versions for a date, we select one which spans longest timerange
    # TODO alternative can be combining all versions into longest non overlaping sequence or just random select
    longest_version_intervals = []
    max_total_length = 0
    # TODO here we assume that within same version we have no overlaps
    # TODO if this is not the case, check for overlaps before calculating total length?
    for version in intervals_per_version:
        total_length = 0
        for interval in intervals_per_version[version]:
            total_length += interval.length()
        if total_length > max_total_length:
            longest_version_intervals = intervals_per_version[version]

    # sort intervals, mark overlaps and split into groups if time range between them is too large
    tree = it.IntervalTree()
    has_overlaps = False
    for interval in longest_version_intervals:
        if tree.overlaps(interval):
            has_overlaps = True
        tree.add(interval)

    return list(map(lambda i: i.data, sorted(tree))), has_overlaps


def get_grouped_filenames(channel, exchange, instrument_type, symbol, start_date=None, end_date=None, compaction='raw'):
    sorted_filenames, has_overlaps = get_sorted_filenames(channel, exchange, instrument_type, symbol, start_date, end_date, compaction)
    return _group_filenames(sorted_filenames), has_overlaps


def _group_filenames(sorted_filenames):
    groups = []
    cur_group = []
    for i in range(0, len(sorted_filenames)):
        cur = sorted_filenames[i]
        cur_group.append(cur)
        if i < len(sorted_filenames) - 1:
            next = sorted_filenames[i + 1]
            if _time_diff(cur, next) > GROUP_TIME_DIFF_S:
                groups.append(cur_group)
                cur_group = []
    if len(cur_group) > 0:
        groups.append(cur_group)

    return groups


def get_filenames_for_version(channel, exchange, instrument_type, symbol, version, start_date=None, end_date=None, compaction='raw'):
    # TODO implement this if needed
    return []


def _sanitize_dates(start_date, end_date):
    if start_date is None:
        # set to latest
        start_date = '1999-01-01'
    if end_date is None:
        # set to furthest possible
        end_date = '2999-01-01'

    return start_date, end_date


def _parse_interval(filename):
    # ex. BINANCE*l2_book*BTC-USDT*1659534879.6234548*1659534909.2105565*8e26d2f8b00646feb569b7ee1ad9ab4f.gz.parquet
    split = filename.split('*')
    start = float(split[3])
    end = float(split[4])
    return it.Interval(start, end, data=filename)

def _time_diff(f1, f2):
    # assumig f1 > f2
    if f1 is None or f2 is None:
        return 0
    i1 = _parse_interval(f1)
    i2 = _parse_interval(f2)
    return i2.begin - i1.end

def plot_filename_ranges(filenames):
    for i in range(0, len(filenames)):
        interval = _parse_interval(filenames[i])
        plt.hlines(i, interval.begin, interval.end, lw=4)
    plt.show()
