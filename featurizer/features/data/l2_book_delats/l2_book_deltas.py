from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.definitions.data_models_utils import L2BookDelta
from collections import OrderedDict
from typing import List
from pandas import DataFrame


class L2BookDeltasData(DataSourceDefinition):

    @classmethod
    def parse_events(cls, df: DataFrame, feature_name: str) -> List: # TODO typehint
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
            # TODO define event schema
            orders = []
            for v in df_dict.values():
                # TODO make it a dict and sync with L2BookDelta dataclass
                orders.append((v['side'], v['price'], v['size']))
            # TODO dictify events
            events.append(L2BookDelta(
                # TODO feature_name should be set somewhere upstream automatically
                feature_name=feature_name,
                timestamp=timestamp,
                receipt_timestamp=receipt_timestamp,
                delta=delta,
                orders=orders
            ))

        return events
