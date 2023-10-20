from typing import List, Dict, Optional, Tuple, Type, Callable

from backtester.clock import Clock
from backtester.data.data_generator import DataStreamEvent
from backtester.data.feature_stream.feature_stream_generator import FeatureStreamGenerator
from backtester.inference.inference_loop import InferenceConfig
from backtester.models.instrument import Instrument
from backtester.models.order import Order, OrderSide, OrderType
from backtester.models.portfolio import Portfolio
from backtester.strategy.base import BaseStrategy


class _StatePerInstrument:
    def __init__(self, instrument: Instrument, portfolio: Portfolio, buy_signal_thresh: float,
                 sell_signal_thresh: float, quote_allocation: float, make_order_callable: Callable):
        self.instrument = instrument
        self.quote_allocation = quote_allocation
        base, quote = instrument.to_asset_instruments()
        self.base_wallet = portfolio.get_wallet(base)
        self.quote_wallet = portfolio.get_wallet(quote)
        self.local_min = None
        self.local_max = None
        self.three_vals = []
        self.is_buying = True
        self.buy_signal_thresh = buy_signal_thresh
        self.sell_signal_thresh = sell_signal_thresh
        self.make_order_callable = make_order_callable

    def _is_local_min(self) -> bool:
        if len(self.three_vals) < 3:
            return False
        return self.three_vals[0] > self.three_vals[1] and self.three_vals[2] > self.three_vals[1]

    def _is_local_max(self) -> bool:
        if len(self.three_vals) < 3:
            return False
        return self.three_vals[0] < self.three_vals[1] and self.three_vals[2] < self.three_vals[1]

    def on_price_update(self, mid_price: float) -> Optional[List[Order]]:
        self.three_vals.append(mid_price)
        if len(self.three_vals) > 3:
            self.three_vals.pop(0)

        if self._is_local_min():
            self.local_min = self.three_vals[1]

        if self._is_local_max():
            self.local_max = self.three_vals[1]

        if self.is_buying:
            if self.local_min is not None and mid_price - self.local_min > self.sell_signal_thresh * self.local_min:
                self.is_buying = False
                # reset old vals
                self.local_min = None
                self.local_max = None
                return [self.make_order_callable(
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    instrument=self.instrument,
                    qty=0.9 * self.quote_allocation * self.quote_wallet.free_balance() / mid_price,
                    price=mid_price
                )]
        else:
            if self.local_max is not None and self.local_max - mid_price > self.buy_signal_thresh * self.local_max:
                self.is_buying = True
                # reset old vals
                self.local_min = None
                self.local_max = None
                return [self.make_order_callable(
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    instrument=self.instrument,
                    qty=0.9 * self.base_wallet.free_balance(),
                    price=mid_price
                )]


class BuyLowSellHighStrategy(BaseStrategy):
    def __init__(
        self,
        clock: Clock,
        portfolio: Portfolio,
        params: Optional[Dict] = None,
        instruments: Optional[List[Instrument]] = None,
        inference_config: Optional[InferenceConfig] = None
    ):
        super(BuyLowSellHighStrategy, self).__init__(
            clock=clock,
            portfolio=portfolio,
            params=params,
            instruments=instruments,
            inference_config=inference_config
        )
        # TODO thresholds per instrument?
        self.states: Dict[Instrument, _StatePerInstrument] = {
            instrument: _StatePerInstrument(
                instrument=instrument,
                portfolio=portfolio,
                buy_signal_thresh=params['buy_signal_thresh'],
                sell_signal_thresh=params['sell_signal_thresh'],
                quote_allocation=1/len(instruments), # TODO parametrize
                make_order_callable=self.make_order
            )
            for instrument in instruments
        }

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        all_orders = []
        feature = None
        for instrument in self.states:
            feature = FeatureStreamGenerator.get_feature_for_instrument(data_event, instrument)
            if feature is None:
                continue
            mid_price = data_event.feature_values[feature]['mid_price'] # TODO query data_generator?
            orders = self.states[instrument].on_price_update(mid_price)
            if orders is not None:
                all_orders.extend(orders)

        if feature is None:
            raise ValueError(f'Unable to find feature for any of the provided instruments, event: {data_event}, instruments: {list(self.states.keys())}')

        return all_orders
