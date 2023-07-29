from dataclasses import dataclass
from typing import List, Dict

from simulation.models.instrument import Instrument, AssetInstrument
from simulation.models.wallet import Wallet


@dataclass
class Portfolio:
    wallets: Dict[AssetInstrument, Wallet]
    base: str = 'USDT'

    @classmethod
    def from_config(cls, config: Dict) -> 'Portfolio':
        return Portfolio({}) # TODO

    def get_wallet(self, asset_instrument: AssetInstrument) -> Wallet:
        if asset_instrument not in self.wallets:
            raise ValueError(f'No wallet for {asset_instrument}')
        return self.wallets[asset_instrument]
