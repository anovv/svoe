import pandas as pd
from typing import List, Tuple, Dict, Any
from featurizer.features.definition.data_models_utils import Trade
from collections import OrderedDict


def parse_trades(trades: pd.DataFrame) -> List[Trade]:
    df_dict = trades.to_dict(into=OrderedDict, orient='index')  # TODO use df.values.tolist() instead and check perf?
    res = []
    for v in df_dict.values():
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
