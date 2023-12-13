import pandas as pd

from svoe.featurizer.data_definitions.data_source_definition import DataSourceDefinition
from svoe.featurizer.data_definitions.data_definition import EventSchema
from collections import OrderedDict
from typing import List, Tuple


class CryptotickL2BookIncrementalData(DataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'update_type': str,
            # TODO make it a list of dicts?
            'orders': List[Tuple[float, float, float]]# side, price, size
        }

    @classmethod
    def preprocess_impl(cls, df: pd.DataFrame) -> pd.DataFrame:
        grouped = df.groupby(['timestamp', 'update_type'])
        dfs = [grouped.get_group(x) for x in grouped.groups]
        dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
        events = []
        for i in range(len(dfs)):
            df = dfs[i]
            timestamp = df.iloc[0]['timestamp']
            receipt_timestamp = df.iloc[0]['receipt_timestamp']
            update_type = df.iloc[0]['update_type']
            df_dict = df.to_dict(orient='index', into=OrderedDict)  # TODO use df.values.tolist() instead and check perf?
            orders = []
            for v in df_dict.values():
                orders.append((v['side'], v['price'], v['size']))
            events.append(cls.construct_event(timestamp, receipt_timestamp, update_type, orders))

        return pd.DataFrame(events)
