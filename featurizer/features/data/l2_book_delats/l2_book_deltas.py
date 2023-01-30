from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.data.data_definition import DataDefinition, EventSchema, Event
from collections import OrderedDict
from typing import List, Dict, Tuple, Type
from pandas import DataFrame


class L2BookDeltasData(DataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'delta': bool,
            'orders': List[Tuple[float, float, float]]# side, price, size
        }

    @classmethod
    def parse_events(cls, df: DataFrame) -> List[Event]:
        grouped = df.groupby(['timestamp', 'delta'])
        dfs = [grouped.get_group(x) for x in grouped.groups]
        dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
        events = []
        for i in range(len(dfs)):
            df = dfs[i]
            timestamp = df.iloc[0].timestamp
            receipt_timestamp = df.iloc[0].receipt_timestamp
            delta = df.iloc[0].delta
            # TODO https://stackoverflow.com/questions/7837722/what-is-the-most-efficient-way-to-loop-through-dataframes-with-pandas
            # regarding iteration speed
            # TODO use numba's jit
            # TODO OrderedDict or SortedDict or Dict?
            df_dict = df.to_dict(orient='index', into=OrderedDict)  # TODO use df.values.tolist() instead and check perf?
            orders = []
            for v in df_dict.values():
                orders.append((v['side'], v['price'], v['size']))
            events.append(cls.construct_event(timestamp, receipt_timestamp, delta, orders))

        return events