import awswrangler as wr

DATABASE = 'svoe_glue_db'

# TODO use max_cache_seconds

# To cast to timestamp
# select distinct from_unixtime(timestamp) from l2_book where exchange='BINANCE' and instrument_type='spot' and symbol='BTC-USDT' and date='2022-07-13'

# to get ts diffs
# select ts, date_diff('millisecond', ts, lag(ts) over(order by ts desc)) as diff from (
#     select distinct from_unixtime(timestamp) as ts from ticker where exchange='BINANCE' and instrument_type='spot' and symbol='BTC-USDT' and date='2022-07-13')

def get_all_dates(channel, exchange, instrument_type, symbol):
    df = wr.athena.read_sql_query(
        sql='SELECT DISTINCT date FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol;',
        database=DATABASE,
        params={'table': f'{channel}', 'exchange': f"'{exchange}'", 'instrument_type': f"'{instrument_type}'", 'symbol': f"'{symbol}'"},
        max_cache_seconds=900
    )

    return df




# df = wr.athena.read_sql_query(
#     sql='SELECT count(timestamp) FROM :table; WHERE exchange=:exchange; AND instrument_type=:instrument_type; AND symbol=:symbol;',
#     database=DATABASE,
#     params={'table': 'l2_book', 'exchange': 'BINANCE', 'instrument_type': 'spot', 'symbol': 'BTC-USDT'}
# )

print(get_all_dates('l2_book', 'BINANCE', 'spot', 'BTC-USDT'))