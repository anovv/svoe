from typing import Dict

from simulation.models.instrument import Instrument


class DataGenerator:

    def next(self) -> Dict:
        raise NotImplementedError

    def has_next(self) -> bool:
        raise NotImplementedError

    def get_cur_mid_prices(self) -> Dict[Instrument, float]:
        raise NotImplementedError

    def store_prices(get_cur_mid_prices):
        def get_and_store_cur_mid_prices(self) -> Dict[Instrument, float]:
            cur_mid_prices