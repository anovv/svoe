from typing import List, Tuple

from featurizer.data_catalog.common.data_models.models import InputItemBatch, InputItem
from featurizer.data_definitions.common.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from featurizer.data_definitions.common.trades.trades import TradesData
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from simulation.models.instrument import Instrument

CRYPTOTICK_RAW_BUCKET_NAME = 'svoe-cryptotick-data'


def cryptotick_input_items(file_and_sizes: List[Tuple[str, int]], batch_size: int) -> List[InputItemBatch]:
    grouped_by_data_source_definition = {}
    for raw_path, size_kb in file_and_sizes:
        item = _parse_s3_key(raw_path, size_kb)
        data_source_definition = item[DataSourceBlockMetadata.data_source_definition.name]
        if data_source_definition in grouped_by_data_source_definition:
            if len(grouped_by_data_source_definition[data_source_definition][-1]) == batch_size:
                grouped_by_data_source_definition[data_source_definition].append([])
            grouped_by_data_source_definition[data_source_definition][-1].append(item)
        else:
            grouped_by_data_source_definition[data_source_definition] = [[item]]
    res = []
    batch_id = 0
    for data_source_definition in grouped_by_data_source_definition:
        for batch in grouped_by_data_source_definition[data_source_definition]:
            res.append(({'batch_id': batch_id}, batch))
            batch_id += 1
    return res


def _parse_s3_key(path: str, size_kb) -> InputItem:
    # example quotes/20230201/BINANCE_SPOT_BTC_USDT.csv.gz

    if 'testing' in path:
        instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
        data_source_params = instrument.asdict()
        data_source = Feature([], CryptotickL2BookIncrementalData, data_source_params)
        input_item = {
            DataSourceBlockMetadata.path.name: path,
            DataSourceBlockMetadata.day.name: '01-02-2023',
            DataSourceBlockMetadata.size_kb.name: size_kb,
            DataSourceBlockMetadata.key.name: data_source.key,
            DataSourceBlockMetadata.data_source_definition.name: data_source.data_definition.__name__
        }

        return input_item

    s = path.split('/')
    if s[0] == 'limitbook_full':
        data_source_definition = CryptotickL2BookIncrementalData.__name__
    elif s[0] == 'trades':
        data_source_definition = TradesData.__name__
    else:
        # TODO quotes
        raise ValueError(f'Unknown data_type {s[0]}')

    raw_date = s[1] # YYYYMMDD
    # make DD-MM-YYYY
    day = f'{raw_date[6:8]}-{raw_date[4:6]}-{raw_date[0:4]}'
    file = s[2] # BINANCE_SPOT_BTC_USDT.csv.gz
    f = file.split('_')
    exchange = f[0]
    if f[1] == 'SPOT':
        instrument_type = 'spot'
    else:
        raise ValueError(f'Unknown instrument_type {f[1]}')
    base = f[2]
    quote = f[3].split('.')[0]

    # TODO call cryptofeed lib to construct symbol here?
    symbol = f'{base}-{quote}'

    path = f's3://{CRYPTOTICK_RAW_BUCKET_NAME}/' + path

    instrument = Instrument(exchange, instrument_type, symbol)
    data_source_params = instrument.asdict()
    data_source = Feature([], CryptotickL2BookIncrementalData, data_source_params)
    input_item = {
        DataSourceBlockMetadata.path.name: path,
        DataSourceBlockMetadata.day.name: day,
        DataSourceBlockMetadata.size_kb.name: size_kb,
        DataSourceBlockMetadata.key.name: data_source.key,
        DataSourceBlockMetadata.data_source_definition.name: data_source.data_definition.__name__
    }

    return input_item
