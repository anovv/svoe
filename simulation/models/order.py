from dataclasses import dataclass
from enum import Enum
from typing import Optional

from simulation.models.instrument import Instrument


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"


class OrderType(Enum):
    LIMIT = 'limit'
    MARKET = 'market'

class OrderSide(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

@dataclass
class Order:
    id: str
    type: OrderType
    side: OrderSide
    instrument: Instrument
    price: Optional[float]
    quantity: float
    status: OrderStatus
