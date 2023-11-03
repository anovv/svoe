from typing import Optional, Dict, List

from backtester.clock import Clock
from featurizer.feature_stream.feature_stream_generator import FeatureStreamGenerator, DataStreamEvent
from backtester.inference.inference_loop import InferenceConfig
from backtester.models.instrument import Instrument
from backtester.models.order import Order, OrderSide, OrderType
from backtester.models.portfolio import Portfolio
from backtester.strategy.base import BaseStrategy


class MLStrategy(BaseStrategy):

    def __init__(
        self,
        clock: Clock,
        portfolio: Portfolio,
        params: Optional[Dict] = None,
        instruments: Optional[List[Instrument]] = None,
        inference_config: Optional[InferenceConfig] = None
    ):
        super(MLStrategy, self).__init__(
            clock=clock,
            portfolio=portfolio,
            params=params,
            instruments=instruments,
            inference_config=inference_config
        )
        self.is_buying = True
        self.instrument = self.instruments[0]
        base, quote = self.instrument.to_asset_instruments()
        self.base_wallet = portfolio.get_wallet(base)
        self.quote_wallet = portfolio.get_wallet(quote)

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        buy_delta = self.params['buy_delta']
        sell_delta = self.params['sell_delta']
        cur_price = FeatureStreamGenerator.get_mid_prices_from_event(data_event)[self.instrument]
        prediction, _ = self.inference_loop.get_latest_inference()
        if self.is_buying:
            if prediction - cur_price > buy_delta:
                self.is_buying = False
                return [self.make_order(
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    instrument=self.instrument,
                    qty=0.9 * self.quote_wallet.free_balance() / cur_price,
                    price=cur_price
                )]
        if not self.is_buying:
            if prediction - cur_price < sell_delta:
                self.is_buying = True
                return [self.make_order(
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    instrument=self.instrument,
                    qty=0.9 * self.base_wallet.free_balance(),
                    price=cur_price
                )]