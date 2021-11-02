import pandas as pd
import s3fs
from order_book import OrderBook
from datetime import date

BUCKET = 's3://svoe.test.1'

# https://github.com/TDAmeritrade/stumpy
def list_files(path: str) -> list[str]:
    # return wr.s3.list_directories(path)
    # return wr.s3.list_objects(path)
    s3 = s3fs.S3FileSystem()
    s3.cachable = False
    return s3.ls(path)


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


def l2_sorted(snaps: list[tuple[float, dict]]) -> bool:
    index = -1
    for row in snaps:
        index += 1
        for side in row[1].keys():
            prices = list(row[1][side].keys())
            copy = prices.copy()
            if side == 'bid': #desc
                copy.sort(reverse=True)
                if copy != prices:
                    raise Exception('Mismatch for bid at ts: ' + str(row[0]) + ' index: ' + str(index))
            elif side == 'ask': #asc
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