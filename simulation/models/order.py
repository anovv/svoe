from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"


class Order:
    id: str
    type: str
    side: str
    symbol: str
    price: str
    quantity: str
    status: OrderStatus