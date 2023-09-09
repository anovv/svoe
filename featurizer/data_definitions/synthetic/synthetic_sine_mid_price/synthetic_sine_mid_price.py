import math
from typing import Dict, List

import ciso8601
import numpy as np
import pandas as pd
from pandas import DataFrame
from portion import Interval

from featurizer.blocks.blocks import BlockRangeMeta
from featurizer.data_definitions.data_definition import EventSchema
from featurizer.data_definitions.synthetic_data_source_definition import SyntheticDataSourceDefinition


class SyntheticSineMidPrice(SyntheticDataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'mid_price': float,
        }

    @classmethod
    def gen_synthetic_events(cls, interval: Interval, params: Dict) -> DataFrame:
        start_ts = interval.lower
        end_ts = interval.upper
        step = params['step']
        num_samples = int((end_ts - start_ts) / step)
        timesteps = np.linspace(start_ts, end_ts, num_samples, endpoint=True)
        amplitude = params['amplitude']
        mean = params['mean']
        freq = params['freq']

        # TODO adjust frequency so consequitive blocks end and start at the same point
        mid_prices = amplitude * np.sin(2 * np.pi * freq * timesteps) + mean
        return pd.DataFrame(zip(timesteps, timesteps, mid_prices), columns=['timestamp', 'receipt_timestamp', 'mid_price'])

    @classmethod
    def gen_synthetic_ranges_meta(cls, start_date: str, end_date: str) -> List[BlockRangeMeta]:
        s_in_d = 24 * 60 * 60
        start_ts = ciso8601.parse_datetime(start_date).timestamp()
        end_ts = ciso8601.parse_datetime(end_date).timestamp() + (s_in_d - 1) # last second

        num_days = math.ceil((end_ts - start_ts)/s_in_d)
        splits_per_day = 4
        num_splits = num_days * splits_per_day
        # print(num_splits)
        split_size = int((end_ts - start_ts)/num_splits)
        # print(split_size)
        ranges = []
        cur_start_ts = start_ts
        cur_end_ts = start_ts + split_size
        while cur_start_ts < end_ts:
            if cur_end_ts <= end_ts:
                ranges.append([{
                    'start_ts': cur_start_ts,
                    'end_ts': cur_end_ts,
                }])
            else:
                ranges.append([{
                    'start_ts': cur_start_ts,
                    'end_ts': end_ts,
                }])
            cur_start_ts = cur_end_ts + 0.1 # 100ms diff betweeb blocks
            cur_end_ts = cur_start_ts + split_size

        # TODO why does it execute only 1 block_range?
        # print(ranges)
        # raise
        return ranges