from cryptofeed.defines import BINANCE, COINBASE, BITMEX, OKEX, FTX, BINANCE_FUTURES, PHEMEX, BYBIT, KRAKEN, KRAKEN_FUTURES
from cryptofeed.exchanges import EXCHANGE_MAP
from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING

SPOT = 'S'
FUTURES = 'F'
# B692998Y 3 weeks
class BaseConfigBuilder(object):

    # TOP_20 = ['BTC', 'ETH', 'BNB', 'ADA', 'XRP', 'DOGE', 'DOT', 'BCH', 'UNI', 'LTC', 'LINK', 'MATIC', 'XLM', 'ETC', 'VET', 'TRX', 'EOS', 'FIL', 'SHIB', 'BSV']
    TOP_20 = ['BTC']
    STABLE = ['USDT', 'BUSD', 'USDC']
    FIAT = ['USD', 'GBP', 'RUB', 'CHF']

    def __init__(self):
        self.exchanges_config = {
            # TODO snapshot_interval?
            # TODO depth_interval?
            # TODO explore candle data
            # symbol_gen, max_depth_l2, channels (ticker, trades, l2, l3, liquidations, open_interest, funding), pairs per pod
            BINANCE: {
                SPOT: [self.symbols(BINANCE, SPOT), 100, [TICKER, TRADES, L2_BOOK], 1],
            },
            # COINBASE: {
            #     SPOT: [self.symbols(COINBASE, SPOT), 100, [TICKER, TRADES, L2_BOOK, L3_BOOK], 1],
            # },
            # OKEX: {
            #     SPOT: [self.symbols(OKEX, SPOT), 100, [TICKER, TRADES, L2_BOOK], 1],
            #     # No liquidations
            #     FUTURES: [self.symbols(OKEX, FUTURES), 100, [TICKER, TRADES, L2_BOOK, OPEN_INTEREST, FUNDING], 1],
            # },
            # FTX: {
            #     SPOT: [self.symbols(FTX, SPOT), 100, [TICKER, TRADES, L2_BOOK], 1],
            #     FUTURES: [self.symbols(FTX, FUTURES), 100, [TICKER, TRADES, L2_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING], 1],
            # },
            # BITMEX: {
            #     FUTURES: [self.symbols(BITMEX, FUTURES), 100, [TICKER, TRADES, L2_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING], 1],
            # },
            # BINANCE_FUTURES: {
            #     FUTURES: [self.symbols(BINANCE_FUTURES, FUTURES), 100, [TICKER, TRADES, L2_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING], 1]
            # },
            # PHEMEX: {
            #     SPOT: [self.symbols(PHEMEX, SPOT), 100, [TRADES, L2_BOOK], 1],
            #     # No liquidations, funding, open_interest, ticker
            #     FUTURES: [self.symbols(PHEMEX, FUTURES), 100, [TRADES, L2_BOOK], 1]
            # },
            BYBIT: {
                # No ticker
                FUTURES: [self.symbols(BYBIT, FUTURES), 100, [TRADES, L2_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING], 1]
            },
            KRAKEN: {
                SPOT: [self.symbols(KRAKEN, SPOT), 100, [TICKER, TRADES, L2_BOOK], 1],
            },
            # KRAKEN_FUTURES: {
            #     # No liquidations
            #     FUTURES: [self.symbols(KRAKEN_FUTURES, FUTURES), 100, [TICKER, TRADES, L2_BOOK, OPEN_INTEREST, FUNDING], 1]
            # },
        }

    # TODO add logic to select base currency, abstract duplicate code
    # TODO WRITE TESTS!!!! they always change symbols, need to verify on every re-gen
    def symbols(self, exchange: str, instrument: str) -> list[str]:
        symbols = EXCHANGE_MAP[exchange].symbols()

        if exchange is BINANCE:
            if instrument is not SPOT:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usdt = [*filter(lambda item: len(item.split('-')) == 2 and item.split('-')[1] == 'USDT', symbols)]
            res = []
            for coin in self.TOP_20:
                symbol = coin + '-USDT'
                if symbol in usdt:
                    res.append(symbol)
            return res

        elif exchange is COINBASE:
            if instrument is not SPOT:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usd = [*filter(lambda item: len(item.split('-')) == 2 and item.split('-')[1] == 'USD', symbols)]
            res = []
            for coin in self.TOP_20:
                symbol = coin + '-USD'
                if symbol in usd:
                    res.append(symbol)
            return res

        elif exchange is OKEX:
            if instrument not in [SPOT, FUTURES]:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            if instrument is SPOT:
                usdt = [*filter(lambda item: len(item.split('-')) == 2 and item.split('-')[1] == 'USDT', symbols)]
                res = []
                for coin in self.TOP_20:
                    symbol = coin + '-USDT'
                    if symbol in usdt:
                        res.append(symbol)
                return res

            if instrument is FUTURES:
                usdt_perp = [*filter(lambda item: len(item.split('-')) == 3 and item.split('-')[1] == 'USDT' and item.split('-')[2] == 'PERP', symbols)]
                res = []
                for coin in self.TOP_20:
                    symbol = coin + '-USDT-PERP'
                    if symbol in usdt_perp:
                        res.append(symbol)
                return res

        elif exchange is FTX:
            if instrument not in [SPOT, FUTURES]:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            if instrument is SPOT:
                usd = [*filter(lambda item: len(item.split('-')) == 2 and item.split('-')[1] == 'USD', symbols)]
                res = []
                for coin in self.TOP_20:
                    symbol = coin + '-USD'
                    if symbol in usd:
                        res.append(symbol)
                return res

            if instrument is FUTURES:
                usd_perp = [*filter(lambda item: len(item.split('-')) == 3 and item.split('-')[1] == 'USD' and item.split('-')[2] == 'PERP', symbols)]
                res = []
                for coin in self.TOP_20:
                    symbol = coin + '-USD-PERP'
                    if symbol in usd_perp:
                        res.append(symbol)
                return res

        elif exchange is BITMEX:
            if instrument is not FUTURES:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usd_and_usdt_perp = [*filter(lambda item: len(item.split('-')) == 3 and (item.split('-')[1] == 'USDT' or item.split('-')[1] == 'USD') and item.split('-')[2] == 'PERP', symbols)]
            res = []
            for coin in self.TOP_20:
                symbol_usd = coin + '-USD-PERP'
                symbol_usdt = coin + '-USDT-PERP'
                # TODO figure which one to use
                if symbol_usdt in usd_and_usdt_perp:
                    res.append(symbol_usdt)
                elif symbol_usd in usd_and_usdt_perp:
                    res.append(symbol_usd)
            return res

        elif exchange is BINANCE_FUTURES:
            if instrument is not FUTURES:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usdt_perp = [*filter(lambda item: len(item.split('-')) == 3 and item.split('-')[1] == 'USDT' and item.split('-')[2] == 'PERP', symbols)]
            res = []
            for coin in self.TOP_20:
                symbol = coin + '-USDT-PERP'
                if symbol in usdt_perp:
                    res.append(symbol)
            return res

        elif exchange is PHEMEX:
            if instrument not in [SPOT, FUTURES]:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            if instrument is SPOT:
                usdt = [*filter(lambda item: len(item.split('-')) == 2 and item.split('-')[1] == 'USDT', symbols)]
                res = []
                for coin in self.TOP_20:
                    symbol = coin + '-USDT'
                    if symbol in usdt:
                        res.append(symbol)
                return res

            if instrument is FUTURES:
                usd_perp = [*filter(lambda item: len(item.split('-')) == 3 and item.split('-')[1] == 'USD' and item.split('-')[2] == 'PERP', symbols)]
                res = []
                for coin in self.TOP_20:
                    symbol = coin + '-USD-PERP'
                    if symbol in usd_perp:
                        res.append(symbol)
                return res

        elif exchange is BYBIT:
            if instrument is not FUTURES:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usd_and_usdt_perp = [*filter(lambda item: len(item.split('-')) == 3 and (
                        item.split('-')[1] == 'USDT' or item.split('-')[1] == 'USD') and item.split('-')[2] == 'PERP',
                                    symbols)]
            res = []
            for coin in self.TOP_20:
                symbol_usd = coin + '-USD-PERP'
                symbol_usdt = coin + '-USDT-PERP'
                # TODO figure which one to use
                if symbol_usdt in usd_and_usdt_perp:
                    res.append(symbol_usdt)
                elif symbol_usd in usd_and_usdt_perp:
                    res.append(symbol_usd)
            return res
        elif exchange is KRAKEN:
            if instrument is not SPOT:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usd_and_usdt = [*filter(lambda item: len(item.split('-')) == 2 and (item.split('-')[1] == 'USDT' or item.split('-')[1] == 'USD'), symbols)]
            res = []
            for coin in self.TOP_20:
                symbol_usd = coin + '-USD'
                symbol_usdt = coin + '-USDT'
                # TODO figure which one to use
                if symbol_usdt in usd_and_usdt:
                    res.append(symbol_usdt)
                elif symbol_usd in usd_and_usdt:
                    res.append(symbol_usd)
            return res
        elif exchange is KRAKEN_FUTURES:
            if instrument is not FUTURES:
                raise ValueError('[Symbols gen] Wrong args: ' + exchange + ' ' + instrument)

            usd_perp = [*filter(lambda item: len(item.split('-')) == 3 and item.split('-')[1] == 'USD' and item.split('-')[2] == 'PERP', symbols)]
            res = []
            for coin in self.TOP_20:
                symbol = coin + '-USD-PERP'
                if symbol in usd_perp:
                    res.append(symbol)
            return res
        else:
            raise ValueError('[Symbols gen] Unsupported exchange ' + exchange)
