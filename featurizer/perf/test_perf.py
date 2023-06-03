import pandas as pd

from featurizer.data_definitions.trades.trades import TradesData
from utils.pandas.df_utils import load_df


# test tvi feature caclucaltion using pandas only for vectorization
def test_vectorized_tvi():
    df = load_df(
        's3://svoe-cataloged-data/trades/BINANCE/spot/BTC-USDT/cryptotick/100.0mb/2023-02-01/1675209965-4ea8eeea78da2f99f312377c643e6b491579f852.parquet.gz'
    )

    df['dt'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.set_index('dt')

    # def t(x):
    #     s = 0
    #     for i in x:
    #         s += i
    #     return s

    # d2 = df[df['side'] == 'BUY'].rolling(window=pd.Timedelta('1s'))['amount'].apply(t, raw=True).to_frame(name='1s_sum_buys')
    # events = TradesData.parse_events(df)

    # https://stackoverflow.com/questions/73344153/pandas-join-results-in-mismatch-shape
    df['vol'] = df['price'] * df['amount']
    buys = df[df['side'] == 'BUY']
    buys['1s_sum_buys'] = buys.rolling(window=pd.Timedelta('1s'))['vol'].sum()
    sells = df[df['side'] == 'SELL']
    sells['1s_sum_sells'] = sells.rolling(window=pd.Timedelta('1s'))['vol'].sum()

    dd = pd.merge(df, buys, on=['dt', 'price', 'amount', 'side', 'id'], how='outer')
    dd = dd[['id', 'price', 'amount', 'side', 'timestamp_x', 'receipt_timestamp_x', '1s_sum_buys', 'vol_x']]
    dd = dd.rename(columns={'timestamp_x': 'timestamp', 'receipt_timestamp_x': 'receipt_timestamp', 'vol_x': 'vol'})

    ddd = pd.merge(dd, sells, on=['dt', 'price', 'amount', 'side', 'id'], how='outer')
    ddd = ddd[['id', 'price', 'amount', 'side', 'timestamp_x', 'receipt_timestamp_x', '1s_sum_buys', 'vol_x', '1s_sum_sells']]
    ddd = ddd.rename(columns={'timestamp_x': 'timestamp', 'receipt_timestamp_x': 'receipt_timestamp', 'vol_x': 'vol'})

    # fill with prev vals first
    ddd = ddd.fillna(method='ffill')
    # 0 for unavailable vals
    ddd = ddd.fillna(value=0.0)


    ddd['tvi'] = 2 * (ddd['1s_sum_buys'] - ddd['1s_sum_sells'])/(ddd['1s_sum_buys'] + ddd['1s_sum_sells'])

    print(buys.head(), len(buys))
    print(df.head(), len(df))
    print(dd.head(), len(dd))
    print(ddd.head(), len(ddd))

test_vectorized_tvi()