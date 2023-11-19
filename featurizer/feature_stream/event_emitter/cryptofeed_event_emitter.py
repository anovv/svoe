import asyncio
import functools
from threading import Thread
from typing import Callable, Any, Dict, Tuple, Type, Set, Optional

from cryptofeed import FeedHandler
from cryptofeed.defines import L2_BOOK, TRADES, TICKER
from cryptofeed.exchanges import EXCHANGE_MAP
from cryptofeed.feed import Feed

from featurizer.data_definitions.common.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import \
    CryptofeedL2BookIncrementalData
from featurizer.data_definitions.common.ticker.cryptofeed.cryptofeed_ticker import CryptofeedTickerData
from featurizer.data_definitions.common.trades.cryptofeed.cryptofeed_trades import CryptofeedTradesData
from featurizer.data_definitions.data_definition import Event
from featurizer.data_definitions.data_source_definition import DataSourceDefinition
from featurizer.feature_stream.event_emitter.data_source_event_emitter import DataSourceEventEmitter
from featurizer.features.feature_tree.feature_tree import Feature


class CryptofeedEventEmitter(DataSourceEventEmitter):

    def __init__(self):
        self.callbacks_per_exchange_per_channel: Dict[str, Dict[str, Callable]] = {}
        self.symbols_per_exchange: Dict[str, Set[str]] = {}
        self.feed_handler = FeedHandler(config={'uvloop': True, 'log': {'disabled': True}})
        self.event_loop = asyncio.new_event_loop()
        self.loop_thread = Thread(target=self.start_loop, daemon=True)

    @classmethod
    def instance(cls) -> 'DataSourceEventEmitter':
        return CryptofeedEventEmitter()

    def register_callback(self, feature: Feature, callback: Callable[[Event], Optional[Any]]):
        exchange, symbol, channel = self._parse_data_source_params(feature)
        if exchange in self.callbacks_per_exchange_per_channel:
            if channel in self.callbacks_per_exchange_per_channel:
                raise ValueError(f'{channel} for {exchange} already exists')
            else:
                self.callbacks_per_exchange_per_channel[exchange][channel] = callback
        else:
            self.callbacks_per_exchange_per_channel[exchange] = {channel: callback}

        if exchange in self.symbols_per_exchange:
            self.symbols_per_exchange[exchange].add(symbol)
        else:
            self.symbols_per_exchange[exchange] = {symbol}

    def start_loop(self):
        asyncio.set_event_loop(self.event_loop)
        for exchange in self.symbols_per_exchange:
            feed_class: Type[Feed] = EXCHANGE_MAP[exchange]
            symbols = list(self.symbols_per_exchange[exchange])
            callbacks_per_channel = self.callbacks_per_exchange_per_channel[exchange]
            raw_callbacks = {}
            for channel in callbacks_per_channel:
                callback = callbacks_per_channel[channel]

                async def _cb(obj, receipt_timestamp):
                    event_for_channel = functools.partial(self._cryptofeed_obj_to_event, channel)
                    event = event_for_channel(obj, receipt_timestamp)
                    callback(event)

                raw_callbacks[channel] = _cb
            # TODO for some reason different types of callbacks dont work
            channels = list(callbacks_per_channel.keys())
            feed = feed_class(
                symbols=symbols,
                channels=channels,
                callbacks=raw_callbacks
            )
            self.feed_handler.add_feed(feed)
        self.feed_handler.run(start_loop=True, install_signal_handlers=False)

    def start(self):
        self.loop_thread.start()

    def stop(self):
        self.feed_handler._stop(loop=self.event_loop) # async stop
        self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        self.loop_thread.join(timeout=10)

    # TODO util cryptofeed related stuff ?
    @classmethod
    def _data_source_for_channel(cls, channel: str) -> Type[DataSourceDefinition]:
        if channel == L2_BOOK:
            return CryptofeedL2BookIncrementalData
        elif channel == TRADES:
            return CryptofeedTradesData
        elif channel == TICKER:
            return CryptofeedTickerData
        else:
            raise ValueError(f'No data_source_def for channel: {channel}')

    @classmethod
    def _channel_for_data_source(cls, data_source: Type[DataSourceDefinition]) -> str:
        if data_source == CryptofeedL2BookIncrementalData:
            return L2_BOOK
        elif data_source == CryptofeedTradesData:
            return TRADES
        elif data_source == CryptofeedTickerData:
            return TICKER
        else:
            raise ValueError(f'No channel for data_source: {data_source}')

    @classmethod
    def _parse_data_source_params(cls, feature: Feature) -> Tuple[str, str, str]:
        data_source_def = feature.data_definition
        params = feature.params
        channel = cls._channel_for_data_source(data_source_def)
        return (params['exchange'], params['symbol'], channel)

    @classmethod
    def _cryptofeed_obj_to_event(cls, channel: str, obj, receipt_timestamp) -> Event:
        d = obj.to_dict()
        args = [obj.timestamp, receipt_timestamp]

        data_source_def = cls._data_source_for_channel(channel)

        if data_source_def == CryptofeedTickerData:
            args.extend([float(d['bid']), float(d['ask'])])
            # {'exchange': 'BINANCE', 'symbol': 'BTC-USDT', 'bid': Decimal('35600.62000000'),
            #  'ask': Decimal('35600.63000000'), 'timestamp': 1700032092.916736}
        elif data_source_def == CryptofeedTradesData:
            if 'side' not in d:
                print(d)
                print(channel)
                raise
            # print(d)
            # raise
            # {'exchange': 'BINANCE', 'symbol': 'BTC-USDT', 'side': 'sell', 'amount': Decimal('1.12359000'),
            #  'price': Decimal('35600.62000000'), 'id': '2757135063', 'type': None, 'timestamp': 1700032092.821}
            args.extend([str(d['side']), float(d['amount']), float(d['price']), str(d['id'])])
        elif data_source_def == CryptofeedL2BookIncrementalData:
            # TODO we need to return deltas or snapshot based on some param (e.g time window)
            raise NotImplementedError
        return data_source_def.construct_event(*args)


