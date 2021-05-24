from cryptofeed.symbols import gen_symbols
from cryptofeed.defines import BINANCE, COINBASE, KRAKEN, HUOBI, DERIBIT, BITMEX, OKEX, FTX, BINANCE_FUTURES


# Core logic for pair generation
class BaseConfigBuilder(object):

    def __init__(self):
        self.exchanges_config = {
            # pair_gen, max_depth_l2, include_ticker, include l3, include futures data
            BINANCE : [self._get_binance_pairs()[:2], 100, True, False, False], #max_depth 5000 # https://github.com/bmoscon/cryptostore/issues/156 set limit to num pairs to avoid rate limit?
            COINBASE: [self._get_coinbase_pairs()[:1], 100, True, True, False],
            OKEX: [self.get_okex_pairs()[:2], 100, True, False, False],
            FTX: [self.get_ftx_pairs()[:1], 100, True, False, False],

            # TODO add funding, open_interest and liquidations
            BITMEX: [self.get_bitmex_pairs()[:1], 100, True, False, True],
            BINANCE_FUTURES: [self.get_binance_futures_pairs()[:1], 100, True, False, True]
            # KRAKEN: [self._get_kraken_pairs()[:40], 100, True, False], #max_depth 1000
            # HUOBI: [self._get_huobi_pairs()[:40], 100, False, False],
            # 'BITMEX' : BITMEX,
            # 'DERIBIT' : DERIBIT
        }

    # TODO refactor below to remove dependency on exchnage specific logic, move to separate class
    @staticmethod
    def _get_kraken_pairs() -> list[str]:
        symbols = gen_symbols(KRAKEN)

        # USD quote only
        return [*filter(lambda item: item.split('-')[1] == 'USD', list(symbols.keys()))]

    @staticmethod
    def _get_coinbase_pairs() -> list[str]:
        symbols = gen_symbols(COINBASE)

        # USD quote only
        return [*filter(lambda item: item.split('-')[1] == 'USD', list(symbols.keys()))]

        # from ccxt
        # c = coinbase()
        # markets = c.fetch_markets()
        # usd_only = list(filter(lambda item: item['symbol'].split('/')[1] == 'USD', markets))
        # usd_only_symbols = list(map(lambda item: item['symbol'], usd_only))

        # return usd_only_symbols

    @staticmethod
    def _get_binance_pairs() -> list[str]:
        symbols = gen_symbols(BINANCE)

        # USD quote only
        return [*filter(lambda item: item.split('-')[1] == 'USDT', list(symbols.keys()))]

    @staticmethod
    def _get_huobi_pairs() -> list[str]:
        symbols = gen_symbols(HUOBI)

        # USD quote only
        return [*filter(lambda item: item.split('-')[1] == 'USDT', list(symbols.keys()))]

    @staticmethod
    def get_okex_pairs():
        symbols = gen_symbols(OKEX)
        return [*filter(lambda item: item.split('-')[1] == 'USDT', list(symbols.keys()))]


    @staticmethod
    def get_ftx_pairs():
        symbols = gen_symbols(FTX)
        return [*filter(lambda item: len(item.split('-')) == 2 and item.split('-')[1] == 'USDT', list(symbols.keys()))]


    @staticmethod
    def get_bitmex_pairs():
        # symbols = gen_symbols(BITMEX)
        return ['BTC-USD', 'ETH-USD', 'XRP-USD', 'DOGE-USDT', 'BNB-USDT']

    @staticmethod
    def get_binance_futures_pairs():
        symbols = gen_symbols(BINANCE_FUTURES)
        return [*filter(lambda item: item.split('-')[1] == 'USDT', list(symbols.keys()))]

    @staticmethod
    def get_deribit_pairs():
        symbols = gen_symbols(DERIBIT)
        print(symbols)


