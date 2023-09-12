import math
from typing import Dict, List

import ciso8601
import numpy as np
import pandas as pd
from pandas import DataFrame
from portion import Interval

from common.time.utils import split_time_range_between_ts, SECONDS_IN_DAY, date_str_to_ts
from featurizer.blocks.blocks import BlockRangeMeta, interval_to_meta
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

        # TODO adjust frequency so consecutive blocks end and start at the same point
        mid_prices = amplitude * np.sin(2 * np.pi * freq * timesteps) + mean
        return pd.DataFrame(zip(timesteps, timesteps, mid_prices), columns=['timestamp', 'receipt_timestamp', 'mid_price'])

    @classmethod
    def gen_synthetic_ranges_meta(cls, start_date: str, end_date: str) -> List[BlockRangeMeta]:
        # s_in_d = 24 * 60 * 60
        # start_ts = ciso8601.parse_datetime(start_date).timestamp()
        # end_ts = ciso8601.parse_datetime(end_date).timestamp() + (s_in_d - 1) # last second
        #
        # num_days = math.ceil((end_ts - start_ts)/s_in_d)
        # splits_per_day = 4
        # num_splits = num_days * splits_per_day
        # split_size = int((end_ts - start_ts)/num_splits)
        # _range = []
        # cur_start_ts = start_ts
        # cur_end_ts = start_ts + split_size
        # while cur_start_ts < end_ts:
        #     if cur_end_ts <= end_ts:
        #         _range.append({
        #             'start_ts': cur_start_ts,
        #             'end_ts': cur_end_ts,
        #         })
        #     else:
        #         _range.append({
        #             'start_ts': cur_start_ts,
        #             'end_ts': end_ts,
        #         })
        #     cur_start_ts = cur_end_ts + 0.1 # 100ms diff betweeb blocks
        #     cur_end_ts = cur_start_ts + split_size
        #
        # return [_range]

        start_ts = date_str_to_ts(start_date)
        end_ts = date_str_to_ts(end_date)
        num_days = math.ceil((end_ts - start_ts) / SECONDS_IN_DAY)
        splits_per_day = 4 # random
        num_splits = num_days * splits_per_day

        splits = split_time_range_between_ts(start_ts, end_ts, num_splits, 0.1)

        return [[interval_to_meta(s) for s in splits]]
