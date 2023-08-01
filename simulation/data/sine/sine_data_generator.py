from typing import Dict

import numpy as np

from simulation.data.data_generator import DataGenerator
from simulation.models.instrument import Instrument


class SineDataGenerator(DataGenerator):

    def __init__(self, instrument: Instrument, start_ts: float, end_ts: float, step: float):

        num_samples = int((end_ts - start_ts)/step)
        timesteps = np.linspace(start_ts, end_ts, num_samples, endpoint=True)
        amplitude = 2000
        mean = 10000
        frequency = int(num_samples/5000)
        mid_prices = amplitude * np.sin(2 * np.pi * frequency * timesteps) + mean

        self.instrument = instrument
        self.data = [{
            'timestamp': timesteps[i],
            'mid_price': mid_prices[i]
        } for i in range(len(timesteps))]

        self.cur_position = -1

    def next(self) -> Dict:
        if self.has_next():
            self.cur_position += 1
            return self.data[self.cur_position]
        else:
            raise ValueError('Reached end of generator')

    def has_next(self) -> bool:
        return self.cur_position < len(self.data) - 1

    def get_cur_mid_prices(self) -> Dict[Instrument, float]:
        if self.cur_position < 0:
            raise ValueError('Call next before getting mid_prices')
        return {self.instrument: self.data[self.cur_position]['mid_price']}
