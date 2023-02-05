from pathlib import Path
from typing import Dict, List, Tuple

from cache_df import CacheDF

from featurizer.features.blocks.blocks import BlockRangeMeta, BlockRange
from featurizer.features.data.l2_book_delats.l2_book_deltas import L2BookDeltasData
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import Feature
from utils.pandas.df_utils import load_files, time_range, get_size_kb, get_len
from featurizer.features.loader.l2_snapshot_utils import get_info


def mock_feature(position: int):
    return Feature(
        [],
        position,
        FeatureDefinition,
        {}
    )


def mock_meta(start_ts, end_ts, extra=None):
    # TODO make mock function
    res = {'start_ts': start_ts, 'end_ts': end_ts}
    if extra:
        res.update(extra)
    return res


def mock_l2_book_deltas_data_ranges_meta(
    block_len_ms, num_blocks, between_blocks_ms=100, cur_ts=0
) -> Dict[Feature, BlockRangeMeta]:
    res = {}
    ranges = []
    for i in range(0, num_blocks):
        meta = mock_meta(cur_ts, cur_ts + block_len_ms)
        if i % 2 == 0:
            # TODO sync keys with L2BookSnapshotFeatureDefinition.group_dep_ranges
            meta['snapshot_ts'] = cur_ts + 10 * 1000
        ranges.append(meta)
        cur_ts += block_len_ms
        cur_ts += between_blocks_ms

    data_params = {} # TODO mock
    data = Feature([], 0, L2BookDeltasData, data_params)
    res[data] = ranges
    return res


def mock_trades_data_and_meta() -> Tuple[Dict[Feature, BlockRange], Dict[Feature, BlockRangeMeta]]:
    consec_athena_files_BINANCE_FUTURES_ETH_USD_PERP = [
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120235.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120264.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120294.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120324.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120354.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120384.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120415.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120444.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120474.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120504.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120534.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120564.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120594.parquet',
        's3://svoe.test.1/parquet/BINANCE_FUTURES/trades/ETH-USDT/BINANCE_FUTURES-trades-ETH-USDT-1622120624.parquet'
    ]
    block_range = _load_and_cache(consec_athena_files_BINANCE_FUTURES_ETH_USD_PERP)
    block_range_meta = []
    for i in range(len(consec_athena_files_BINANCE_FUTURES_ETH_USD_PERP)):
        # TODO util this
        block = block_range[i]
        _time_range = time_range(block)
        block_range_meta.append({
            'len_s': _time_range[0],
            'start_ts': _time_range[1],
            'end_ts': _time_range[2],
            'size_kb': get_size_kb(block),
            'len': get_len(block),
            'path': consec_athena_files_BINANCE_FUTURES_ETH_USD_PERP[i],
        })

    data_params = {  }# TODO mock
    data = Feature([], 0, TradesData, data_params)
    return {data: block_range}, {data: block_range_meta}


def mock_l2_book_delta_data_and_meta() -> Tuple[Dict[Feature, BlockRange], Dict[Feature, BlockRangeMeta]]:
    consec_athena_files_BINANCE_FUTURES_BTC_USD_PERP = [
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778796.722228*1664778826.607931*2e74bf76915c4b168248b18d059773b1.gz.parquet',
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778826.710401*1664778856.692907*4ffb70c161f4429d81663ca70d070ccc.gz.parquet',
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778856.819425*1664778887.340147*9b0e6bf57fc34074a662e3db00aebfae.gz.parquet',
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778887.442283*1664778919.106682*49d157f8d4134b409ba0126b008250b3.gz.parquet',
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778919.204879*1664778949.1246562*c04cc54b0c094afd922c53ccf6344651.gz.parquet',
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778949.313781*1664778979.103868*f3605c1202f64eb3bca1960eb5b9b241.gz.parquet',
        's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=BTC-USDT-PERP/base=BTC/quote=USDT/date=2022-10-03/compaction=raw/version=local/BINANCE_FUTURES*l2_book*BTC-USDT-PERP*1664778979.1611981*1664779009.082793*71c48c0b589d4c0b9ee2961dde59d9a1.gz.parquet'
    ]
    block_range = _load_and_cache(consec_athena_files_BINANCE_FUTURES_BTC_USD_PERP)

    infos = [get_info(block) for block in block_range]
    block_range_meta = []
    for i in range(len(consec_athena_files_BINANCE_FUTURES_BTC_USD_PERP)):
        block_meta = {
            'path': consec_athena_files_BINANCE_FUTURES_BTC_USD_PERP[i],
            'start_ts': infos[i]['time_range'][1],
            'end_ts': infos[i]['time_range'][2],
        }
        if 'snapshot_ts' in infos[i]:
            block_meta['snapshot_ts'] = infos[i]['snapshot_ts']
        block_range_meta.append(block_meta)

    data_params = {  }# TODO mock
    data = Feature([], 0, L2BookDeltasData, data_params)
    return {data: block_range}, {data: block_range_meta}


# TODO util this
def _load_and_cache(files: List[str]) -> BlockRange:
    print(f'Loading {len(files)} blocks for testing...')
    # check cache first
    cache_location = './cached_dfs'
    Path(cache_location).mkdir(parents=True, exist_ok=True)
    # TODO use joblib.Memory instead
    cache = CacheDF(cache_dir=cache_location)
    block_range = []
    cached_paths = []
    for path in files:
        hashed_path = hash(path)  # can't use s3:// strings as keys, cache_df lib flips out
        if cache.is_cached(hashed_path):
            block_range.append(cache.read(hashed_path))
            cached_paths.append(path)
    print(f'Loaded {len(cached_paths)} cached dataframes')
    if len(cached_paths) != len(files):
        to_load_paths = list(set(files) - set(cached_paths))
        loaded = load_files(to_load_paths)
        # cache loaded dfs
        for i in range(len(to_load_paths)):
            cache.cache(loaded[i], hash(to_load_paths[i]))
        block_range.extend(loaded)
        print(f'Loaded and cached {len(loaded)} dataframes')

    return block_range