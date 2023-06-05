import time
from typing import Tuple

import matplotlib.pyplot as plt
import pandas as pd
from portion import closed
from streamz import Stream

from featurizer.calculator.tasks import merge_blocks
from featurizer.data_definitions.trades.trades import TradesData
from featurizer.features.definitions.tvi.trade_volume_imb_fd import TradeVolumeImbFD
from featurizer.features.feature_tree.feature_tree import construct_feature_tree
from utils.pandas.df_utils import load_df, time_range, is_ts_sorted
from utils.streamz.stream_utils import run_named_events_stream


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
    window = '1m'
    b_key = f'{window}_sum_buys'
    s_key = f'{window}_sum_sells'
    df['vol'] = df['price'] * df['amount']
    buys = df[df['side'] == 'BUY']
    buys[b_key] = buys.rolling(window=pd.Timedelta(window))['vol'].sum()
    sells = df[df['side'] == 'SELL']
    sells[s_key] = sells.rolling(window=pd.Timedelta(window))['vol'].sum()

    # TODO can only merge on id
    dd = pd.merge(df, buys, on=['dt', 'price', 'amount', 'side', 'id'], how='outer')
    dd = dd[['id', 'price', 'amount', 'side', 'timestamp_x', 'receipt_timestamp_x', b_key, 'vol_x']]
    dd = dd.rename(columns={'timestamp_x': 'timestamp', 'receipt_timestamp_x': 'receipt_timestamp', 'vol_x': 'vol'})

    # TODO can only merge on id
    ddd = pd.merge(dd, sells, on=['dt', 'price', 'amount', 'side', 'id'], how='outer')
    ddd = ddd[['id', 'price', 'amount', 'side', 'timestamp_x', 'receipt_timestamp_x', b_key, 'vol_x', s_key]]
    ddd = ddd.rename(columns={'timestamp_x': 'timestamp', 'receipt_timestamp_x': 'receipt_timestamp', 'vol_x': 'vol'})

    # fill with prev vals first
    ddd = ddd.fillna(method='ffill')
    # 0 for unavailable vals
    ddd = ddd.fillna(value=0.0)

    ddd['tvi'] = 2 * (ddd[b_key] - ddd[s_key])/(ddd[b_key] + ddd[s_key])
    ddd = ddd[['tvi', 'timestamp']]
    # ddd = ddd.groupby('dt').first()
    ddd = ddd.resample('1s').first()
    print(ddd.head())
    print(len(ddd))
    # print(buys.head(), len(buys))
    # print(df.head(), len(df))
    # print(dd.head(), len(dd))
    # print(ddd.head(), len(ddd))
    # ddd.plot(x='timestamp', y='tvi')
    # plt.show()

def test_streaming_tvi():
    feature_params = {0: {'window': '1m', 'sampling': '1s'}}
    feature_tvi = construct_feature_tree(TradeVolumeImbFD, feature_params, {})
    data_trades = construct_feature_tree(TradesData, {}, {})
    df = load_df(
        's3://svoe-cataloged-data/trades/BINANCE/spot/BTC-USDT/cryptotick/100.0mb/2023-02-01/1675209965-4ea8eeea78da2f99f312377c643e6b491579f852.parquet.gz'
    )
    tr = time_range(df)
    interval = closed(tr[1], tr[2])
    deps = {data_trades: [df]}
    t = time.time()
    merged = merge_blocks(deps)
    print(f'Merged in {time.time() - t}s')
    # construct upstreams
    upstreams = {dep_feature: Stream() for dep_feature in deps.keys()}
    s = feature_tvi.feature_definition.stream(upstreams, feature_tvi.params)
    if isinstance(s, Tuple):
        out_stream = s[0]
        state = s[1]
    else:
        out_stream = s

    t = time.time()
    df = run_named_events_stream(merged, upstreams, out_stream, interval)
    print(f'Events run in {time.time() - t}s')
    print(df.head())


def test_rust_tvi():
    import svoe_rust
    df = load_df(
        's3://svoe-cataloged-data/trades/BINANCE/spot/BTC-USDT/cryptotick/100.0mb/2023-02-01/1675209965-4ea8eeea78da2f99f312377c643e6b491579f852.parquet.gz'
    )
    # rust expects tuples (id, timestamp, amount, price, side)
    df = df[['id', 'timestamp', 'amount', 'price', 'side']]
    l = list(df.itertuples(index=False, name=None))
    # l = l[:10000]
    window_s = 60
    t = time.time()
    slow_res = svoe_rust.calc_tvi(l, window_s)
    print(f'Slow finished in {time.time() - t}s')
    print(f'Slow len: {len(slow_res)}')
    t = time.time()
    fast_res = svoe_rust.calc_tvi_fast(l, window_s)
    print(f'Fast finished in {time.time() - t}s')
    print(f'Fast len: {len(fast_res)}')

    # TODO why different results?
    print(slow_res == fast_res)
    diff = list(set(slow_res) - set(fast_res))
    print(len(diff))
    print(diff[:5])
    # print(df.head())

def test_t():
    df = load_df(
        's3://svoe-cataloged-data/trades/BINANCE/spot/BTC-USDT/cryptotick/100.0mb/2023-02-01/1675209965-4ea8eeea78da2f99f312377c643e6b491579f852.parquet.gz'
    )
    # rust expects tuples (id, timestamp, amount, price, side)
    df = df[['id', 'timestamp', 'amount', 'price', 'side']]

    t1 = time.time()
    l = list(df.itertuples(index=False, name=None))
    print(f'Step1: {time.time() - t1}s')
    t2 = time.time()
    ll = list(map(lambda e: {'timestamp': e[1], 'amount': e[2], 'price': e[3], 'side': e[4]}, l))
    print(f'Step2: {time.time() - t2}s')

def test_tt():
    df = load_df(
        's3://svoe-cataloged-data/trades/BINANCE/spot/BTC-USDT/cryptotick/100.0mb/2023-02-01/1675209965-4ea8eeea78da2f99f312377c643e6b491579f852.parquet.gz'
    )
    # TradesData.parse_events(df)
    print(is_ts_sorted(df))




# test_rust_tvi()
test_vectorized_tvi()
# test_streaming_tvi()
# test_t()
# test_tt()