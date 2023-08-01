from typing import Dict

import numpy as np

from simulation.data.data_generator import DataGenerator


class SineDataGenerator(DataGenerator):

    def __init__(self, start_ts: float, end_ts: float, step: float):

        num_samples = int((end_ts - start_ts)/step)
        timesteps = np.linspace(start_ts, end_ts, num_samples, endpoint=True)
        amplitude = 1000
        mean = 10000
        frequency = int(num_samples/5000)
        mid_prices = amplitude * np.sin(2 * np.pi * frequency * timesteps) + mean

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
