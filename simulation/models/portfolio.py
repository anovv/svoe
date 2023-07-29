from dataclasses import dataclass
from typing import List, Dict

from simulation.models.wallet import Wallet


@dataclass
class Portfolio:
    wallets: List[Wallet]
    base: str = 'USDT'

    @classmethod
    def from_config(cls, config: Dict) -> 'Portfolio':
        return Portfolio([]) # TODO
