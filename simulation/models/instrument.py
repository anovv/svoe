from dataclasses import dataclass


@dataclass
class Instrument:
    exchange: str
    instrument_type: str
    symbol: str
