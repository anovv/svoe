import yaml

from pydantic.dataclasses import dataclass
from typing import List, Dict

from simulation.models.instrument import AssetInstrument
from simulation.models.wallet import Wallet, WalletBalance


@dataclass
class Portfolio:
    wallets: List[Wallet]
    quote: AssetInstrument

    @classmethod
    def load_config(cls, path: str) -> 'Portfolio':
        with open(path, 'r') as stream:
            d = yaml.safe_load(stream)
            return Portfolio(**d)

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


@dataclass
class PortfolioBalanceRecord:
    timestamp: float
    total: float
    per_wallet: Dict[AssetInstrument, WalletBalance]
