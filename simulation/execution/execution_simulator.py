from typing import List

from simulation.models.order import Order


class ExecutionSimulator:

    def execute(self, orders: List[Order]):
        raise NotImplementedError


