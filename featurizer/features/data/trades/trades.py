from collections import OrderedDict
from typing import Tuple, List

from pandas import DataFrame

from featurizer.features.data.data_definition import EventSchema, Event
from featurizer.features.data.data_source_definition import DataSourceDefinition


class TradesData(DataSourceDefinition):

    # TODO do we need timestamp-based aggregation here?
    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            # TODO make it a list of dicts
            'trades': List[Tuple[str, float, float, str, str]]# side, amount, price, order_type, id
        }

    @classmethod
    def parse_events(cls, df: DataFrame) -> List[Event]:
        # TODO merge this logic with L2BookDeltaData parse_events
        grouped = df.groupby(['timestamp'])
        dfs = [grouped.get_group(x) for x in grouped.groups]
        dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
        events = []
        for i in range(len(dfs)):
            df = dfs[i]
            timestamp = df.iloc[0].timestamp
            receipt_timestamp = df.iloc[0].receipt_timestamp
            df_dict = df.to_dict(orient='index', into=OrderedDict)  # TODO use df.values.tolist() instead and check perf?
            trades = []
            for v in df_dict.values():
                trades.append((v['side'], v['amount'], v['price'], v['order_type'], v['id']))
            events.append(cls.construct_event(timestamp, receipt_timestamp, trades))


        return events