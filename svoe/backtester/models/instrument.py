from pydantic.dataclasses import dataclass
from typing import Tuple


# TODO util this
def _parse_symbol(symbol: str) -> Tuple[str, str]:
    s = symbol.split('-')
    return s[0], s[1]


def _compose_symbol(base: str, quote: str) -> str:
    return base + '-' + quote


# instead of symbol (pair of assets) it has single asset. Used in wallets
@dataclass(frozen=True, eq=True)
class AssetInstrument:
    exchange: str
    instrument_type: str
    asset: str


@dataclass(frozen=True, eq=True)
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

    @classmethod
    def from_asset_instruments(cls, base: AssetInstrument, quote: AssetInstrument) -> 'Instrument':
        if base.exchange != quote.exchange:
            raise ValueError('instruments should be of same exchange')
        if base.instrument_type != quote.instrument_type:
            raise ValueError('instruments should be of same instrument_type')
        return Instrument(
            exchange=base.exchange,
            instrument_type=base.instrument_type,
            symbol=_compose_symbol(base.asset, quote.asset)
        )
