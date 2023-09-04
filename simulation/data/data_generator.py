from typing import Dict

from simulation.models.instrument import Instrument


class DataGenerator:

    def next(self) -> Dict:
        raise NotImplementedError

    def has_next(self) -> bool:
        raise NotImplementedError

    def get_cur_mid_prices(self) -> Dict[Instrument, float]:
        raise NotImplementedError