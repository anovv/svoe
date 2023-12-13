from dataclasses import dataclass

from svoe.backtester.models.instrument import Instrument
from svoe.backtester.models.order import OrderSide, OrderType


@dataclass
class Trade:
    trade_id: str
    order_id: str
    timestamp: float
    instrument: Instrument
    side: OrderSide
    trade_type: OrderType
    quantity: float
    price: float
    commission: float
