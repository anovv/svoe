from typing import List, Tuple

from data_catalog.common.data_models.models import InputItemBatch, InputItem
from data_catalog.common.utils.sql.models import DataCatalog
from utils.s3.s3_utils import list_files_and_sizes_kb

CRYPTOTICK_RAW_BUCKET_NAME = 'svoe-cryptotick-data'


def cryptotick_input_items(batch_size: int) -> List[InputItemBatch]:
    raw_files = list_files_and_sizes_kb(CRYPTOTICK_RAW_BUCKET_NAME)
    grouped_by_data_type = {}
    for raw_path, size_kb in raw_files:
        item = _parse_s3_key(raw_path, size_kb)
        data_type = item[DataCatalog.data_type.name]
        if data_type in grouped_by_data_type:
            if len(grouped_by_data_type[data_type][-1]) == batch_size:
                grouped_by_data_type[data_type].append([])
            grouped_by_data_type[data_type][-1].append(item)
        else:
            grouped_by_data_type[data_type] = [[item]]
    res = []
    batch_id = 0
    for data_type in grouped_by_data_type:
        for batch in grouped_by_data_type[data_type]:
            res.append(({'batch_id': batch_id}, batch))
            batch_id += 1
    return res


def _parse_s3_key(key: str, size_kb) -> InputItem:
    # example quotes/20230201/BINANCE_SPOT_BTC_USDT.csv.gz
    s = key.split('/')
    if s[0] == 'limitbook_full':
        data_type = 'l2_book' # TODO l2_inc
    elif s[0] == 'quotes':
        data_type = 'ticker' # TODO l2_inc
    elif s[0] == 'trades':
        data_type = 'trades' # TODO l2_inc
    else:
        raise ValueError(f'Unknown data_type {s[0]}')

    date = s[1] # YYYY-MM-DD
    # make DD-MM-YYYY
    date = f'{date[6:8]}-{date[4:6]}-{date[0:4]}'
    file = s[2] # BINANCE_SPOT_BTC_USDT.csv.gz
    f = file.split('_')
    exchange = f[0]
    if f[1] == 'SPOT':
        instrument_type = 'spot'
    else:
        raise ValueError(f'Unknown instrument_type {f[1]}')
    base = f[2]
    quote = f[3]

    # TODO call cryptofeed lib to construct symbol here?
    symbol = f'{base}-{quote}'

    return {
        DataCatalog.data_type.name: data_type,
        DataCatalog.exchange.name: exchange,
        DataCatalog.symbol: symbol,
        DataCatalog.base: base,
        DataCatalog.quote: quote,
        DataCatalog.compaction: '100mb',
        DataCatalog.source: 'cryptotick',
        DataCatalog.date: date,
        DataCatalog.size_kb: size_kb
    }



