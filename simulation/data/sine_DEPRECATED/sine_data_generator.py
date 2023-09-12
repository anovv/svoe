from typing import Dict, List

import numpy as np

from simulation.data.data_generator import DataStreamGenerator
from simulation.models.instrument import Instrument


# TODO deprecate this, create SineFD feature definition and use FeatureStreamGenerator instead
class SineDataStreamGenerator(DataStreamGenerator):

    def __init__(self, instrument: Instrument, timesteps: List[float], mid_prices: List[float]):
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

    @classmethod
    def from_time_range(cls, instrument: Instrument, start_ts: float, end_ts: float, step: float):
        num_samples = int((end_ts - start_ts) / step)
        timesteps = np.linspace(start_ts, end_ts, num_samples, endpoint=True)
        amplitude = 2000
        mean = 10000
        frequency = int(num_samples / 5000)
        mid_prices = amplitude * np.sin(2 * np.pi * frequency * timesteps) + mean
        return SineDataStreamGenerator(instrument=instrument, timesteps=list(timesteps), mid_prices=mid_prices)

    # @classmethod
    # def split(cls, instrument: Instrument, start_ts: float, end_ts: float, step: float, num_splits: int) -> List[
    #     'DataStreamGenerator']:
    #     num_samples = int((end_ts - start_ts) / step)
    #     timesteps = np.linspace(start_ts, end_ts, num_samples, endpoint=True)
    #     amplitude = 2000
    #     mean = 10000
    #     frequency = int(num_samples / 5000)
    #     mid_prices = amplitude * np.sin(2 * np.pi * frequency * timesteps) + mean
    #
    #     split_ts = np.array_split(timesteps, num_splits)
    #     split_mid_prices = np.array_split(mid_prices, num_splits)
    #
    #     if len(split_ts) != len(split_mid_prices):
    #         raise ValueError('Failed to split sine data: ts and price size mismatch')
    #
    #     generators = []
    #     for i in range(len(split_ts)):
    #         _timesteps = split_ts[i]
    #         _mid_prices = split_mid_prices[i]
    #         generators.append(SineDataStreamGenerator(
    #             instrument=instrument,
    #             timesteps=_timesteps,
    #             mid_prices=_mid_prices
    #         ))
    #
    #     return generators


