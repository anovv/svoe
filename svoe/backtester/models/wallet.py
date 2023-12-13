from collections import namedtuple

from pydantic.dataclasses import dataclass, Field
from typing import Dict

from svoe.backtester.models.instrument import AssetInstrument


# TODO add Ledger class to keep track of all executed Trade instances

WalletBalance = namedtuple('WalletBalance', ['free', 'locked'])

@dataclass
class Wallet:
    asset_instrument: AssetInstrument
    balance: float
    locked: Dict[str, float] = Field(default_factory=dict)

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

    def locked_balance(self) -> float:
        res = 0
        for order_id in self.locked:
            res += self.locked[order_id]
        return res

    # includes locked
    def total_balance(self) -> float:
        return self.balance + self.locked_balance()

    def free_balance(self) -> float:
        return self.balance

    def get_free_and_locked_balance(self) -> WalletBalance:
        return WalletBalance(self.free_balance(), self.locked_balance())
