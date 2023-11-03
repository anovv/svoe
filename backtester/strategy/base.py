import uuid
from typing import List, Optional, Dict, Any

from backtester.clock import Clock
from featurizer.feature_stream.feature_stream_generator import DataStreamEvent
from backtester.models.instrument import Instrument
from backtester.models.order import Order, OrderSide, OrderType, OrderStatus
from backtester.models.portfolio import Portfolio
from backtester.inference.inference_loop import InferenceLoop, InferenceConfig


class BaseStrategy:

    def __init__(self,
        clock: Clock,
        portfolio: Portfolio,
        params: Optional[Dict] = None,
        instruments: Optional[List[Instrument]] = None,
        inference_config: Optional[InferenceConfig] = None
    ):
        self.clock = clock
        self.portfolio = portfolio
        self.latest_data_event = None
        self.inference_loop: Optional[InferenceLoop] = None
        self.inference_config = inference_config
        self.params = params
        self.instruments = instruments

        if self.inference_config is not None:
            self.inference_loop = InferenceLoop(self.get_latest_inference_input_values, self.inference_config, self.clock)

    def get_latest_inference_input_values(self) -> List[Any]:
        # TODO figure out how to preserve order
        feature_values = []
        if self.latest_data_event is not None:
            for feature in self.latest_data_event.feature_values:
                for name in self.latest_data_event.feature_values[feature]:
                    if name not in ['timestamp', 'receipt_timestamp']:
                        feature_values.append(self.latest_data_event.feature_values[feature][name])
        return feature_values

    def run_inference_loop(self):
        if self.inference_loop is not None:
            self.inference_loop.run()

    def stop_inference_loop(self):
        if self.inference_loop is not None:
            self.inference_loop.stop()

    # wrapper
    def on_data(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        self.latest_data_event = data_event
        return self.on_data_udf(data_event)

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        raise NotImplementedError

    # TODO move to execution engine?
    def make_order(self, side: OrderSide, order_type: OrderType, instrument: Instrument, qty: float, price: float) -> Order:
        order_id = str(uuid.uuid4())
        # lock quantities
        base_instr, quote_instr = instrument.to_asset_instruments()
        base_wallet = self.portfolio.get_wallet(base_instr)
        quote_wallet = self.portfolio.get_wallet(quote_instr)
        # qty is base_qty
        if side == OrderSide.BUY:
            # we lock quote
            quote_qty = price * qty
            quote_wallet.lock_from_balance(order_id=order_id, qty=quote_qty)
        else:
            base_wallet.lock_from_balance(order_id=order_id, qty=qty)

        return Order(
            order_id=order_id,
            type=order_type,
            side=side,
            instrument=instrument,
            price=price,
            quantity=qty,
            status=OrderStatus.OPEN
        )
