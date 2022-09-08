import awswrangler as wr

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

# TODO handle data versioning
def get_s3_filenames(channel, exchange, instrument_type, symbol, start_date, end_date):
    if start_date < 0:
        # set to latest
        start_date = '1999-01-01'
    if end_date < 0:
        # set to furthest possible
        end_date = '2999-01-01'
    df = wr.athena.read_sql_query(
        sql='SELECT DISTINCT "$path" FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol; AND date >= :start; AND date <= :end;',
        database=DATABASE,
        params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'", 'symbol': f"'{symbol}'", 'start': f"'{start_date}'", 'end': f"'{end_date}'"},
        max_cache_seconds=900
    )

    # TODO are these sorted
    return df



# df = wr.athena.read_sql_query(
#     sql='SELECT count(timestamp) FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol;',
#     database=DATABASE,
#     params={'table': 'l2_book', 'exchange': 'BINANCE', 'instrument_type': 'spot', 'symbol': 'BTC-USDT'}
# )

# print(get_all_dates('l2_book', 'BINANCE', 'spot', 'BTC-USDT'))

print(get_s3_filenames('l2_book', 'BINANCE', 'spot', 'BTC-USDT', -1, -1))