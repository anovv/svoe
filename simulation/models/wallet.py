from dataclasses import dataclass, field
from typing import Dict

from simulation.models.instrument import AssetInstrument


# TODO add Ledger class to keep track of all executed Trade instances
@dataclass
class Wallet:
    asset_instrument: AssetInstrument
    balance: float
    locked: Dict[str, float] = field(default_factory=dict) # values locked in open orders, order_id -> qty

    def lock_from_balance(self, order_id: str, qty: float):
        if qty > self.balance:
            raise ValueError(f'Can not lock {order_id}: qty {qty} is larger then balance {self.balance}')
        if order_id in self.locked:
            raise ValueError(f'Can not lock {order_id} twice')

        self.locked[order_id] = qty
        self.balance -= qty

    def unlock(self, order_id: str) -> float:
        if order_id not in self.locked:
            raise ValueError(f'Can not unlock {order_id}: does not exist')
        qty = self.locked[order_id]
        del self.locked[order_id]
        return qty

    def unlock_to_balance(self, order_id: str):
        qty = self.unlock(order_id)
        self.balance += qty

    def deposit(self, qty: float):
        self.balance += qty

    def withdraw(self, qty: float):
        if qty > self.balance:
            raise ValueError(f'Can not withdraw {qty}: not enough funds')
        self.balance -= qty
