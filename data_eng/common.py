import dask.dataframe
import pandas as pd
import s3fs
from order_book import OrderBook
from datetime import date, datetime
import dask.dataframe as dd
import dask.array as da

import numpy as np
from numba import jit
from numba import float64
from numba import int64

import tqdm

BUCKET = 's3://svoe.test.1'


# https://github.com/TDAmeritrade/stumpy
def list_files(path: str) -> list[str]:
    # return wr.s3.list_directories(path)
    # return wr.s3.list_objects(path)
    s3 = s3fs.S3FileSystem()
    s3.cachable = False
    return s3.ls(path)


# groups files in buckets by dates
# lens = {k: len(v) for k, v in dates.items()}
def group_by_date(files: list[str]) -> dict:
    res = {}
    for file in files:
        date = _date(file)
        if date in res:
            res[date].append(file)
        else:
            res[date] = [file]

    return res


# 'svoe.test.1/parquet/BINANCE_FUTURES/l2_book/ADA-USDT/BINANCE_FUTURES-l2_book-ADA-USDT-1625077342.parquet'
def _date(file: str) -> str:
    ts = int(file.split('-')[-1].split('.')[0])
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')


def _ob_to_snap(ob: OrderBook, timestamp: float) -> dict:
    snapshot = {'timestamp': timestamp}

    bid_prices = ob.bids
    ask_prices = ob.asks
    if len(bid_prices) != len(ask_prices):
        print('Bid/ask size mismatch for ts ' + str(timestamp))

    if bid_prices.index(0)[0] >= ask_prices.index(0)[0]:
        print('Bid ask overlap for ts ' + str(timestamp))

    for level in range(max(len(bid_prices), len(ask_prices))):
        if level < len(bid_prices):
            price_bid = bid_prices.index(level)[0]
            size_bid = ob.bids[price_bid]
            snapshot['bid[' + str(level) + '].price'] = price_bid
            snapshot['bid[' + str(level) + '].size'] = size_bid
        if level < len(ask_prices):
            price_ask = ask_prices.index(level)[0]
            size_ask = ob.asks[price_ask]
            snapshot['ask[' + str(level) + '].price'] = price_ask
            snapshot['ask[' + str(level) + '].size'] = size_ask

    # old
    # for side in ['bid', 'ask']:
    #     level = 0
    #     for price in ob[side]:
    #         size = ob[side][price]
    #         snapshot[side + str(level) + '_price'] = price
    #         snapshot[side + str(level) + '_size'] = size
    #         level += 1

    return snapshot


def l2_snaps_dask(deltas: dd.DataFrame) -> da.Array:
    dask.dataframe.append()
    dask.dataframe.read_parquet()
    snapshots = da.from_array([])
    current_timestamp = 0.0
    found_first_snapshot = False
    ob = OrderBook()

    it = deltas.itertuples()

    while (row := next(it, None)) is not None:
        is_snapshot = row.delta == 'False'  # TODO check dtype of delta

        # skip first rows until we find a snapshot # is this needed?
        if not found_first_snapshot:
            if is_snapshot:
                found_first_snapshot = True
                current_timestamp = row.timestamp
                print("First snapshot row index: " + str(row.Index))
            else:
                continue

        timestamp = row.timestamp
        if current_timestamp != timestamp:
            snapshots.append(_ob_to_snap(ob, current_timestamp))
            current_timestamp = timestamp

        side = row.side
        price = row.price  # TODO use Decimals?
        size = row.size
        if size == 0.0:
            if price in ob[side]:
                del ob[side][price]
            else:
                # TODO should this happen? Data inconsistent?
                print('boink')
        else:
            ob[side][price] = size

    # Append last
    snapshots.append(_ob_to_snap(ob, current_timestamp))

    return snapshots


def l2_snaps(deltas: pd.DataFrame) -> list[tuple[float, dict]]:
    if not _validate_l2_deltas_df(deltas):
        raise Exception('Dataframe is not valid')
    snapshots = []
    current_timestamp = 0.0
    found_first_snapshot = False
    ob = OrderBook()

    it = deltas.itertuples()

    while (row := next(it, None)) is not None:
        is_snapshot = row.delta == 'False'  # TODO check dtype of delta

        # skip first rows until we find a snapshot # is this needed?
        if not found_first_snapshot:
            if is_snapshot:
                found_first_snapshot = True
                current_timestamp = row.timestamp
                print("First snapshot row index: " + str(row.Index))
            else:
                continue

        timestamp = row.timestamp
        if current_timestamp != timestamp:
            snapshots.append(_ob_to_snap(ob, current_timestamp))
            current_timestamp = timestamp

        side = row.side
        price = row.price  # TODO use Decimals?
        size = row.size
        if size == 0.0:
            if price in ob[side]:
                del ob[side][price]
            else:
                # TODO should this happen? Data inconsistent?
                print('boink')
        else:
            ob[side][price] = size

    # Append last
    snapshots.append(_ob_to_snap(ob, current_timestamp))

    return snapshots


def l2_is_sorted(snaps: list[tuple[float, dict]]) -> bool:
    index = -1
    for row in snaps:
        index += 1
        for side in row[1].keys():
            prices = list(row[1][side].keys())
            copy = prices.copy()
            if side == 'bid':  # desc
                copy.sort(reverse=True)
                if copy != prices:
                    raise Exception('Mismatch for bid at ts: ' + str(row[0]) + ' index: ' + str(index))
            elif side == 'ask':  # asc
                copy.sort()
                if copy != prices:
                    raise Exception('Mismatch for ask at ts: ' + str(row[0]) + ' index: ' + str(index))
            else:
                raise Exception('Side should be ask or bid')

    return True


# TODO
def l2_hist(snaps: list[tuple[float, dict]]) -> tuple[dict, dict]:
    hist_ask = {}
    hist_bid = {}
    for row in snaps:
        bid_key = 'bid_' + str(len(row[1]['bid']))
        ask_key = 'ask_' + str(len(row[1]['ask']))

        if ask_key in hist_ask:
            hist_ask[ask_key] += 1
        else:
            hist_ask[ask_key] = 1

        if bid_key in hist_bid:
            hist_bid[bid_key] += 1
        else:
            hist_bid[bid_key] = 1

    return hist_ask, hist_bid


def _validate_l2_deltas_df(deltas: pd.DataFrame) -> bool:
    # TODO
    # 1. Make sure delta==False groups have the same timestamp in group
    # 2. Make sure delta==False groups have the same number of unique price levels (depth) in group (bids and asks)
    # 3. Make sure delta==False groups are sorted by price (bids and asks)
    # 4. Check overlap of best bid/ask prices
    return True


def load_df(exchange: str, symbol: str, channel: str, start: date, end: date) -> pd.DataFrame:
    # TODO
    return None


def get_available_time_range(exchange: str, symbol: str, channel: str) -> list[tuple[date, date]]:
    # TODO
    return None


# TODO move away

@jit((float64[:], int64), nopython=True, nogil=True)
def ewma(arr_in, window):
    r"""Exponentialy weighted moving average specified by a decay ``window``
    to provide better adjustments for small windows via:

        y[t] = (x[t] + (1-a)*x[t-1] + (1-a)^2*x[t-2] + ... + (1-a)^n*x[t-n]) /
               (1 + (1-a) + (1-a)^2 + ... + (1-a)^n).

    Parameters
    ----------
    arr_in : np.ndarray, float64
        A single dimenisional numpy array
    window : int64
        The decay window, or 'span'

    Returns
    -------
    np.ndarray
        The EWMA vector, same length / shape as ``arr_in``

    Examples
    --------
    >>> import pandas as pd
    >>> a = np.arange(5, dtype=float)
    >>> exp = pd.DataFrame(a).ewm(span=10, adjust=True).mean()
    >>> np.array_equal(_ewma_infinite_hist(a, 10), exp.values.ravel())
    True
    """
    n = arr_in.shape[0]
    ewma = np.empty(n, dtype=float64)
    alpha = 2 / float(window + 1)
    w = 1
    ewma_old = arr_in[0]
    ewma[0] = ewma_old
    for i in range(1, n):
        w += (1-alpha)**i
        ewma_old = ewma_old*(1-alpha) + arr_in[i]
        ewma[i] = ewma_old / w
    return ewma


@jit((float64[:], int64), nopython=True, nogil=True) # this one is faster
def ewma_infinite_hist(arr_in, window):
    r"""Exponentialy weighted moving average specified by a decay ``window``
    assuming infinite history via the recursive form:

        (2) (i)  y[0] = x[0]; and
            (ii) y[t] = a*x[t] + (1-a)*y[t-1] for t>0.

    This method is less accurate that ``_ewma`` but
    much faster:

        In [1]: import numpy as np, bars
           ...: arr = np.random.random(100000)
           ...: %timeit bars._ewma(arr, 10)
           ...: %timeit bars._ewma_infinite_hist(arr, 10)
        3.74 ms ± 60.2 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
        262 µs ± 1.54 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

    Parameters
    ----------
    arr_in : np.ndarray, float64
        A single dimenisional numpy array
    window : int64
        The decay window, or 'span'

    Returns
    -------
    np.ndarray
        The EWMA vector, same length / shape as ``arr_in``

    Examples
    --------
    >>> import pandas as pd
    >>> a = np.arange(5, dtype=float)
    >>> exp = pd.DataFrame(a).ewm(span=10, adjust=False).mean()
    >>> np.array_equal(_ewma_infinite_hist(a, 10), exp.values.ravel())
    True
    """
    n = arr_in.shape[0]
    ewma = np.empty(n, dtype=float64)
    alpha = 2 / float(window + 1)
    ewma[0] = arr_in[0]
    for i in range(1, n):
        ewma[i] = arr_in[i] * alpha + ewma[i-1] * (1 - alpha)
    return ewma