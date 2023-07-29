from dataclasses import dataclass


@dataclass
class Instrument:
    exchange: str
    instrument_type: str
    symbol: str

# instead of symbol (pair of assets) it has single asset. Used in walltes
@dataclass
class AssetInstrument:
    exchange: str
    instrument_type: str
    asset: str

