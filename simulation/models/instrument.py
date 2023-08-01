from dataclasses import dataclass
from typing import Tuple


# TODO util this
def _parse_symbol(symbol: str) -> Tuple[str, str]:
    s = symbol.split('-')
    return s[0], s[1]


# instead of symbol (pair of assets) it has single asset. Used in walltes
@dataclass
class AssetInstrument:
    exchange: str
    instrument_type: str
    asset: str


@dataclass
class Instrument:
    exchange: str
    instrument_type: str
    symbol: str

    def to_asset_instruments(self) -> Tuple[AssetInstrument, AssetInstrument]:
        base, quote = _parse_symbol(self.symbol)
        return AssetInstrument(
            exchange=self.exchange,
            instrument_type=self.instrument_type,
            asset=base
        ), AssetInstrument(
            exchange=self.exchange,
            instrument_type=self.instrument_type,
            asset=quote
        )

