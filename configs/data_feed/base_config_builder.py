from cryptofeed.symbols import gen_symbols
from cryptofeed.defines import BINANCE, COINBASE, KRAKEN, HUOBI, DERIBIT, BITMEX


# Core logic for pair generation
class BaseConfigBuilder(object):

    def __init__(self):
        self.exchanges_config = {
            # pair_gen, max_depth_l2, include_ticker, include l3
            # BINANCE : [self._get_binance_pairs()[:4], 100, True, False], #max_depth 5000 # https://github.com/bmoscon/cryptostore/issues/156 set limit to num pairs to avoid rate limit?
            # COINBASE: [self._get_coinbase_pairs()[:4], 100, True, True],
            # KRAKEN: [self._get_kraken_pairs()[:4], 100, True, False], #max_depth 1000
            HUOBI: [self._get_huobi_pairs()[:4], 100, False, False],
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
    def get_deribit_pairs():
        symbols = gen_symbols(DERIBIT)
        print(symbols)

    @staticmethod
    def get_bitmex_pairs():
        symbols = gen_symbols(BITMEX)
        print(symbols)
