from datetime import datetime

import numpy as np
import pandas as pd

from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.data.data_definition import DataDefinition, EventSchema, Event
from collections import OrderedDict
from typing import List, Dict, Tuple, Type


class CryptotickL2BookIncrementalData(DataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'update_type': str,
            # TODO make it a list of dicts
            'orders': List[Tuple[float, float, float]]# side, price, size
        }

    @classmethod
    def parse_events(cls, df: pd.DataFrame, **kwargs) -> List[Event]:
        # TODO for some reason raw crypottick dates are not sorted
        # calc timestamps
        # date_str = kwargs['date_str'] # 20230201
        # TODO pass this
        date_str = '20230201'
        datetime_str = f'{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} ' #yyyy-mm-dd
        df['time_exchange'] = datetime_str + df['time_exchange']
        df['time_coinapi'] = datetime_str + df['time_coinapi']
        # https://stackoverflow.com/questions/54313463/pandas-datetime-to-unix-timestamp-seconds
        df['timestamp'] = pd.to_datetime(df['time_exchange']).astype(int)/10**9
        df['receipt_timestamp'] = pd.to_datetime(df['time_coinapi']).astype(int)/10**9

        # group
        grouped = df.groupby(['time_exchange', 'update_type'])
        dfs = [grouped.get_group(x) for x in grouped.groups]
        dfs = sorted(dfs, key=lambda df: df['time_exchange'].iloc[0], reverse=False)
        events = []
        misses = []
        diffs = []
        for i in range(len(dfs)):
            df = dfs[i]
            timestamp = df.iloc[0]['timestamp']
            receipt_timestamp = df.iloc[0]['receipt_timestamp']
            update_type = df.iloc[0]['update_type']
            df_dict = df.to_dict(orient='index', into=OrderedDict)  # TODO use df.values.tolist() instead and check perf?
            orders = []
            for v in df_dict.values():
                side = 'bid' if v['is_buy'] == 1 else 'ask'
                price = v['entry_px']
                size = v['entry_sx']
                orders.append((side, price, size))
            events.append(cls.construct_event(timestamp, receipt_timestamp, update_type, orders))
            if i > 0:
                if dfs[i - 1].iloc[0]['timestamp'] > dfs[i].iloc[0]['timestamp']:
                    misses.append((dfs[i - 1].iloc[0]['time_exchange'], dfs[i].iloc[0]['time_exchange']))
                diffs.append(float(dfs[i].iloc[0]['timestamp']) - float(dfs[i - 1].iloc[0]['timestamp']))

        print(misses)
        print(len(misses))
        print(np.mean(diffs))

        return events
