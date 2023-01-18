from featurizer.features.data.data import Data
from typing import List, OrderedDict
from pandas import DataFrame

class L2BookDeltasData(Data):

    # TODO define event schema

    @classmethod
    def params(cls):
        return {} # TODO

    @classmethod
    def parse_events(cls, df: DataFrame) -> List: # TODO typehint
        grouped = df.groupby(['timestamp', 'delta'])
        dfs = [grouped.get_group(x) for x in grouped.groups]
        dfs = sorted(dfs, key=lambda df: df['timestamp'].iloc[0], reverse=False)
        events = []
        for i in range(len(dfs)):
            df = dfs[i]
            timestamp = df.iloc[0].timestamp
            receipt_timestamp = df.iloc[0].receipt_timestamp
            delta = df.iloc[0].delta
            orders = []
            # TODO https://stackoverflow.com/questions/7837722/what-is-the-most-efficient-way-to-loop-through-dataframes-with-pandas
            # regarding iteration speed
            # TODO use numba's jit
            # TODO OrderedDict or SortedDict or Dict?
            df_dict = df.to_dict(into=OrderedDict,
                                 orient='index')  # TODO use df.values.tolist() instead and check perf?
            # TODO define event schema
            events.append({
                'timestamp': timestamp,
                'receipt_timestamp': receipt_timestamp,
                'delta': delta,
                'orders': list(df_dict.values())# {'side': side, 'price': price, 'size': size}
            })

        return events
