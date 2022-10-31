import pandas as pd
from typing import List, Tuple, Dict, Any
from featurizer.features.definitions.data_models_utils import Trade
from collections import OrderedDict
from tqdm import tqdm


def parse_trades(trades: pd.DataFrame) -> List[Trade]:
    df_dict = trades.to_dict(into=OrderedDict)  # TODO use df.values.tolist() instead and check perf?
    res = []
    vals = list(df_dict.values())
    for i in tqdm(range(len(vals))):
        v = vals[i]
        print(v)
        res.append(Trade(
            timestamp=v['timestamp'],
            receipt_timestamp=v['receipt_timestamp'],
            side=v['side'],
            amount=v['amount'],
            price=v['price'],
            id=v['id'],
            type=v['type']
        ))
    return res
