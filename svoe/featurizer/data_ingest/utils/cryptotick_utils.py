import dataclasses
from typing import List, Optional

import ciso8601
import pandas as pd

from svoe.featurizer.data_ingest.config import FeaturizerDataIngestConfig
from svoe.featurizer.data_ingest.models import InputItemBatch, InputItem

from svoe.common.pandas.df_utils import is_ts_sorted
from svoe.featurizer.data_definitions.common.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import \
    CryptotickL2BookIncrementalData
from svoe.featurizer.features.feature_tree.feature_tree import Feature
from svoe.featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from svoe.featurizer.sql.models.data_source_metadata import DataSourceMetadata
from svoe.backtester.models.instrument import Instrument

CRYPTOTICK_RAW_BUCKET_NAME = 'svoe-cryptotick-data'


def cryptotick_input_items(config: FeaturizerDataIngestConfig) -> List[InputItemBatch]:
    batch_size = config.batch_size
    grouped_by_data_source_definition = {}
    for data_source_files in config.data_source_files:
        data_source_definition = data_source_files.data_source_definition
        for raw_path, size_kb in data_source_files.files_and_sizes:
            item = _parse_s3_key(raw_path, size_kb, data_source_definition)
            if item is None:
                continue
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
            res.append(InputItemBatch(
                batch_id,
                batch
            ))
            batch_id += 1
    return res


def _parse_s3_key(path: str, size_kb, data_source_definition) -> Optional[InputItem]:
    # example quotes/20230201/BINANCE_SPOT_BTC_USDT.csv.gz

    if 'testing' in path:
        instrument = Instrument('BINANCE', 'spot', 'BTC-USDT')
        data_source_params = dataclasses.asdict(instrument)
        data_source = Feature([], CryptotickL2BookIncrementalData, data_source_params)
        input_item = {
            DataSourceBlockMetadata.path.name: path,
            DataSourceBlockMetadata.day.name: '01-02-2023',
            DataSourceBlockMetadata.size_kb.name: size_kb,
            DataSourceBlockMetadata.key.name: data_source.key,
            DataSourceBlockMetadata.data_source_definition.name: data_source.data_definition.__name__,
            DataSourceMetadata.params.name: data_source_params
        }

        # TODO return input_item if we test pipeline
        return None

    s = path.split('/')

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
    data_source_params = dataclasses.asdict(instrument)
    data_source = Feature([], data_source_definition, data_source_params)
    input_item = {
        DataSourceBlockMetadata.path.name: path,
        DataSourceBlockMetadata.day.name: day,
        DataSourceBlockMetadata.size_kb.name: size_kb,
        DataSourceBlockMetadata.key.name: data_source.key,
        DataSourceBlockMetadata.data_source_definition.name: data_source_definition.__name__,
        DataSourceMetadata.params.name: data_source_params
    }

    return input_item


def process_cryptotick_timestamps(df: pd.DataFrame, date_str: Optional[str] = None) -> pd.DataFrame:
    if date_str is not None:
        # certain data_types from cryptotick (e.g. L2 book) do not include date into time_exchange column (only hours/m/s...)
        # so it needs to be passed from upstream
        # date_str = dd-mm-yyyy '01-02-2023'
        datetime_str = f'{date_str[6:10]}-{date_str[3:5]}-{date_str[0:2]}T'  # yyyy-mm-dd + 'T'
    else:
        datetime_str = ''

    def _to_ts(s):
        return ciso8601.parse_datetime(f'{datetime_str}{s}Z').timestamp()

    df['timestamp'] = df['time_exchange'].map(lambda x: _to_ts(x))
    df['receipt_timestamp'] = df['time_coinapi'].map(lambda x: _to_ts(x))

    # for some reason raw cryptotick dates are not sorted
    # don't use inplace=True as it harms perf https://sourcery.ai/blog/pandas-inplace/
    df = df.sort_values(by=['timestamp'], ignore_index=True)
    if not is_ts_sorted(df):
        raise ValueError('Unable to sort df by timestamp')

    df = df.drop(columns=['time_exchange', 'time_coinapi'])

    return df
