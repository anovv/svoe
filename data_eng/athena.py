import awswrangler as wr
import pprint

DATABASE = 'svoe_glue_db'

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

def get_all_dates(channel, exchange, instrument_type, symbol):
    df = wr.athena.read_sql_query(
        sql='SELECT DISTINCT date FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol;',
        database=DATABASE,
        params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'", 'symbol': f"'{symbol}'"},
        max_cache_seconds=900
    )

    return df


def select_versions(channel, exchange, instrument_type, symbol, start_date=None, end_date=None, compaction='raw', version_selector='random'):
    start_date, end_date = _sanitize_dates(start_date, end_date)
    if version_selector == 'random':
        # in case we have multiple versions being stored at the same date
        # (i.e parallel data feeds with different configurations)
        # we select one at random, this avoid duplicate entries and data overlaps
        df = wr.athena.read_sql_query(
            sql='SELECT DISTINCT versions FROM ('
                '   SELECT date, arbitrary(version) as versions FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol; AND date >= :start; AND date <= :end; AND compaction=:compaction; GROUP BY date'
                ')',
            database=DATABASE,
            params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'",
                    'symbol': f"'{symbol}'", 'start': f"'{start_date}'", 'end': f"'{end_date}'", 'compaction':  f"'{compaction}'"},
            max_cache_seconds=900
        )
        return df

    # TODO implement alternative selection logic
    raise ValueError('Unsupported version selector')


def get_s3_filenames(channel, exchange, instrument_type, symbol, start_date=None, end_date=None, compaction='raw', version_selector='random'):
    start_date, end_date = _sanitize_dates(start_date, end_date)
    # versions = select_versions(channel, exchange, instrument_type, symbol, start_date, end_date, compaction, version_selector)
    # versions_list = versions['versions'].to_list()
    # versions_list = ['testing-551b73ef015edc54438bfdb219710e859e71749c', 'testing ', 'local',
    #  'testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0']
    df = wr.athena.read_sql_query(
        sql='SELECT DISTINCT "$path" FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol; AND date >= :start; AND date <= :end; AND compaction=:compaction; ORDER BY "$path"',
        database=DATABASE,
        params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'", 'symbol': f"'{symbol}'", 'start': f"'{start_date}'", 'end': f"'{end_date}'", 'compaction':  f"'{compaction}'"},
        max_cache_seconds=900
    )

    return df


def _sanitize_dates(start_date, end_date):
    if start_date is None:
        # set to latest
        start_date = '1999-01-01'
    if end_date is None:
        # set to furthest possible
        end_date = '2999-01-01'

    return start_date, end_date

# pp = pprint.PrettyPrinter()
# print(get_all_dates('l2_book', 'BINANCE', 'spot', 'BTC-USDT'))
# pp.pprint(get_s3_filenames('l2_book', 'BINANCE', 'spot', 'BTC-USDT', start_date='2022-08-03', end_date='2022-08-03')['$path'].to_list())

# print(select_versions('l2_book', 'BINANCE', 'spot', 'BTC-USDT'))