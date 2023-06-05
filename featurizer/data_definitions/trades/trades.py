import time
from collections import OrderedDict
from typing import Tuple, List, Dict

from pandas import DataFrame

from featurizer.data_definitions.data_definition import EventSchema, Event
from featurizer.data_definitions.data_source_definition import DataSourceDefinition


class TradesData(DataSourceDefinition):

    # TODO do we need timestamp-based aggregation here?
    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            # TODO make it a list of dataclasses?
            'trades': List[Dict] # side, amount, price, id
        }

    @classmethod
    def parse_events(cls, df: DataFrame, **kwargs) -> List[Event]:
        # TODO merge this logic with L2BookDeltaData parse_events
        t = time.time()
        grouped = df.groupby(['timestamp'])
        print(f'Step1: {time.time() - t}s')
        t = time.time()
        dfs = [grouped.get_group(x) for x in grouped.groups]
        print(f'Step2: {time.time() - t}s')
        t = time.time()
        dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
        print(f'Step3: {time.time() - t}s')
        t = time.time()
        events = []
        for i in range(len(dfs)):
            df = dfs[i]
            timestamp = df.iloc[0].timestamp
            receipt_timestamp = df.iloc[0].receipt_timestamp
            df_dict = df.to_dict(orient='index', into=OrderedDict)  # TODO use df.values.tolist() instead and check perf?
            trades = []
            for v in df_dict.values():
                trades.append({k: v[k] for k in ['side', 'amount', 'price', 'id']})
            events.append(cls.construct_event(timestamp, receipt_timestamp, trades))
        print(f'Step4: {time.time() - t}s')
        t = time.time()

        return events