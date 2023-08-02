import yaml

from pydantic.dataclasses import dataclass
from typing import List, Dict

from simulation.models.instrument import Instrument, AssetInstrument
from simulation.models.wallet import Wallet


@dataclass
class Portfolio:
    # TODO make it a List[Wallet]
    wallets: List[Wallet]
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
        wallet = None
        for w in self.wallets:
            if w.asset_instrument == asset_instrument:
                if wallet is not None:
                    raise ValueError(f'Duplicate wallets for {asset_instrument}')
                wallet = w
        if wallet is None:
            raise ValueError(f'Can not find wallet for {asset_instrument}')
        return wallet
