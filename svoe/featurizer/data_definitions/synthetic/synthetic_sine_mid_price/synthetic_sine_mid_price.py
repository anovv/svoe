from typing import Dict, List

import numpy as np
import pandas as pd
from pandas import DataFrame
from portion import Interval

from svoe.common.time.utils import split_time_range_between_ts, date_str_to_ts
from svoe.featurizer.blocks.blocks import BlockRangeMeta, interval_to_meta
from svoe.featurizer.data_definitions.data_definition import EventSchema
from svoe.featurizer.data_definitions.synthetic_data_source_definition import SyntheticDataSourceDefinition


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
    def gen_synthetic_ranges_meta(cls, start_date: str, end_date: str, num_splits: int) -> List[BlockRangeMeta]:
        start_ts = date_str_to_ts(start_date)
        end_ts = date_str_to_ts(end_date)

        splits = split_time_range_between_ts(start_ts, end_ts, num_splits, 0.1)

        return [[interval_to_meta(s) for s in splits]]
