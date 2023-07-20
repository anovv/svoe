from typing import Dict, Optional
from dataclasses import dataclass


class SimulationEvent:
    timestamp: float


# TODO sync this with events in featurizer
class DataEvent(SimulationEvent):
    exchange: str
    instrument_type: str
    symbol: str
    data_type: str


class SignalEvent(SimulationEvent):
    signal_data: Dict


class OrderEvent(SimulationEvent):
    exchange: str
    instrument_type: str
    symbol: str
    order_type: str
    price: float
    quantity: float
    side: str


class FillEvent(SimulationEvent):
    exchange: str
    instrument_type: str
    symbol: str
    order_type: str
    price: float
    quantity: float
    side: str
    fill_cost: Optional[float] = None
    commission: Optional[float] = None