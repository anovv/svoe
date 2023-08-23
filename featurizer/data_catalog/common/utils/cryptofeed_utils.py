from typing import Generator, Optional, Tuple, Dict
from featurizer.data_catalog.common.data_models.models import InputItemBatch
from featurizer.sql.data_catalog.models import DataCatalog
from common.s3 import inventory

S3_BUCKET = 'svoe.test.1'


def generate_cryptofeed_input_items(batch_size: int) -> Generator[InputItemBatch, None, None]:
    meta = {'batch_id': 0}
    items = []
    for inv_df in inventory():
        for row in inv_df.itertuples():
            d_row = row._asdict()

            size_kb = d_row['size']/1024.0
            input_item = _parse_s3_key(d_row['key'])

            # TODO sync keys with DataCatalog sql model
            input_item['size_kb'] = size_kb
            items.append(input_item)
            if len(items) == batch_size:
                yield meta, items
                items = []
                meta['batch_id'] += 1

    if len(items) != 0:
        yield meta, items


def _parse_s3_key(key: str) -> Optional[Dict]:

    def _parse_symbol(symbol_raw: str, exchange: Optional[str] = None) -> Tuple[str, str, str, str]:
        spl = symbol_raw.split('-')
        base = spl[0]
        quote = spl[1]
        instrument_type = 'spot'
        symbol = symbol_raw
        if len(spl) > 2:
            instrument_type = 'perpetual'

        # FTX special case:
        if exchange == 'FTX' and spl[1] == 'PERP':
            quote = 'USDT'
            instrument_type = 'perpetual'
            symbol = f'{base}-USDT-PERP'
        return symbol, base, quote, instrument_type

    spl = key.split('/')
    if len(spl) < 3:
        return None
    if spl[0] == 'data_lake' and spl[1] == 'data_feed_market_data':
        # case 1
        #  starts with 'data_lake/data_feed_market_data/funding/exchange=BINANCE_FUTURES/instrument_type=perpetual/instrument_extra={}/symbol=ADA-USDT-PERP/base=ADA/quote=USDT/...'
        data_type = spl[2]
        exchange = spl[3].split('=')[1]
        symbol_raw = spl[6].split('=')[1]
        symbol, base, quote, instrument_type = _parse_symbol(symbol_raw, exchange)
    elif spl[0] == 'data_lake' or spl[0] == 'parquet':
        # case 2
        # starts with 'data_lake/BINANCE/l2_book/BTC-USDT/...'
        # starts with 'parquet/BINANCE/l2_book/AAVE-USDT/...'
        exchange = spl[1]
        data_type = spl[2]
        symbol_raw = spl[3]
        symbol, base, quote, instrument_type = _parse_symbol(symbol_raw, exchange)
    else:
        # unparsable
        return None

    return {
        DataCatalog.data_type.name: data_type,
        DataCatalog.exchange.name: exchange,
        DataCatalog.symbol.name: symbol,
        DataCatalog.instrument_type.name: instrument_type,
        DataCatalog.source.name: 'cryptofeed',
        DataCatalog.quote.name: quote,
        DataCatalog.base.name: base,
        DataCatalog.path.name: f's3://{S3_BUCKET}/{key}'
    }
