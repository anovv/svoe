from typing import List, Dict, Optional, Tuple, Type, Callable

from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.definitions.mid_price.mid_price_fd.mid_price_fd import MidPriceFD
from featurizer.features.feature_tree.feature_tree import Feature
from simulation.clock import Clock
from simulation.data.data_generator import DataStreamEvent
from simulation.models.instrument import Instrument
from simulation.models.order import Order, OrderSide, OrderType
from simulation.models.portfolio import Portfolio
from simulation.strategy.base import BaseStrategy


class _StatePerInstrument:
    def __init__(self, instrument: Instrument, portfolio: Portfolio, buy_signal_thresh: float,
                 sell_signal_thresh: float, make_order_callable: Callable):
        self.instrument = instrument
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
                    qty=0.9 * self.quote_wallet.free_balance() / mid_price,
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
    def __init__(self, instruments: List[Instrument], clock: Clock, portfolio: Portfolio, params: Dict):
        super(BuyLowSellHighStrategy, self).__init__(clock, portfolio)
        # TODO thresholds per instrument?
        self.states: Dict[Instrument, _StatePerInstrument] = {
            instrument: _StatePerInstrument(instrument, portfolio, params['buy_signal_thresh'], params['sell_signal_thresh'], self.make_order)
            for instrument in instruments
        }

    # TODO util this?
    @classmethod
    def _get_feature_for_instrument(cls, data_event: DataStreamEvent, feature_definition: Type[FeatureDefinition], instrument: Instrument) -> Feature:
        # TODO cache this to avoid recalculation on each update? or make a FeatureStreamSchema abstraction?
        _feature = None
        for feature in data_event.feature_values:
            if feature.feature_definition != feature_definition:
                continue
            data_deps = feature.get_data_deps()
            if len(data_deps) != 1:
                raise ValueError('Expected exactly 1 data source dependency')
            params = data_deps[0].params

            # TODO make model for params?
            instr = Instrument(
                params['exchange'],
                params['instrument_type'],
                params['symbol'],
            )
            if instr == instrument:
                _feature = feature
        if _feature is None:
            raise ValueError(f'Unable to find feature for {feature_definition} and {instrument}')

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        all_orders = []
        for instrument in self.states:
            feature = self._get_feature_for_instrument(data_event, MidPriceFD, instrument)
            mid_price = data_event.feature_values[feature]['mid_price'] # TODO query data_generator?
            orders = self.states[instrument].on_price_update(mid_price)
            if orders is not None:
                all_orders.extend(orders)

        return all_orders
