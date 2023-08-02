import yaml

from pydantic.dataclasses import dataclass
from typing import List, Dict

from simulation.models.instrument import Instrument, AssetInstrument
from simulation.models.wallet import Wallet


@dataclass
class Portfolio:
    # TODO make it a List[Wallet]
    wallets: Dict[AssetInstrument, Wallet]
    quote: AssetInstrument

    # @classmethod
    # def from_config(cls, config: Dict) -> 'Portfolio':
    #     q = AssetInstrument(exchange='BINANCE', instrument_type='spot', asset='USDT')
    #     return Portfolio(wallets={},quote=quote) # TODO construct wallets from config

    @classmethod
    def load_config(cls, path: str) -> 'Portfolio':
        with open(path, 'r') as stream:
            d = yaml.safe_load(stream)
            return Portfolio(d)

    def get_wallet(self, asset_instrument: AssetInstrument) -> Wallet:
        if asset_instrument not in self.wallets:
            raise ValueError(f'No wallet for {asset_instrument}')
        return self.wallets[asset_instrument]
