from typing import List, Dict, Optional, Generator, Tuple

import pandas as pd
import ray

import utils.s3.s3_utils as s3_utils
from data_catalog.indexer.sql.client import MysqlClient
from data_catalog.indexer.models import InputItem, IndexItem, IndexItemBatch, InputItemBatch

# for pipelined queue https://docs.ray.io/en/latest/ray-core/patterns/pipelining.html
# for backpressure https://docs.ray.io/en/latest/ray-core/patterns/limit-pending-tasks.html
# fro mem usage https://docs.ray.io/en/releases-1.12.0/ray-core/objects/memory-management.html
# memory monitor https://docs.ray.io/en/latest/ray-core/scheduling/ray-oom-prevention.html

INPUT_ITEM_BATCH_SIZE = 1000
WRITE_INDEX_ITEM_BATCH_SIZE = 1000

@ray.remote
class Coordinator:
    input_queue: List[InputItemBatch] = [] # batches of input items, should be checked for existence in Db
    indexable_input_queue: List[InputItem] = [] # non existent input items which should be indexed and ready to download
    to_index_queue: List[pd.DataFrame] = [] # downloaded object refs # TODO or ObjectRefs?
    to_write_index_queue: List[IndexItem] = [] # index items ready wo be written to Db

    def get_input_batch(self) -> Optional[List[InputItem]]:
        if len(self.input_queue) != 0:
            return self.input_queue.pop(0)
        else:
            return None

    def put_indexable_items(self, batch: InputItemBatch):
        self.indexable_input_queue.extend(batch)

    def get_to_write_batch(self) -> Optional[IndexItemBatch]:
        # TODO check if this is the last batch
        if len(self.to_write_index_queue) < WRITE_INDEX_ITEM_BATCH_SIZE:
            return None
        else:
            return self.to_write_index_queue[-WRITE_INDEX_ITEM_BATCH_SIZE:]

    def update_progress(self, info: Dict):
        # TODO
        return

    # main coordinator loop
    def run(self):
        # TODO add backpressure to Driver program, stop when driver queue is empty
        while True:
            # TODO if remote() call blocks, everything below should be separated
            if len(self.indexable_input_queue) != 0:
                to_download = self.indexable_input_queue.pop(0)
                # TODO set resources
                load_and_queue_df.remote(to_download, self.to_index_queue)
            if len(self.to_index_queue) != 0:
                # TODO batch this?
                to_index = self.to_index_queue.pop(0)
                # TODO set resources
                index_and_queue_df.remote(to_index, self.to_write_index_queue)

            # TODO add queues status report here to show on a dashboard (Streamlit?)


@ray.remote
class DbReader:
    def __init__(self, coordinator: Coordinator):
        self.coordinator = coordinator
        self.client = MysqlClient()

    def run(self):
        self.input_item_batch_ref = self.coordinator.get_input_batch.remote()
        while True:
            input_item_batch = ray.get(self.work_item_ref)
            if input_item_batch is None:
                # TODO add sleep so we don't waste CPU cycles
                continue

            # schedule async fetching of next work item to enable compute pipelining
            self.input_item_batch_ref = self.coordinator.get_input_batch.remote()
            # work item is a batch of input items to check if they are already indexed
            non_existent = self.client.check_exists(input_item_batch)
            # TODO do we call ray.get here?
            self.coordinator.put_indexable_items(non_existent).remote()


@ray.remote
class DbWriter:
    def __init__(self, coordinator: Coordinator):
        self.coordinator = coordinator
        self.client = MysqlClient()

    def write_batch(self, batch: List[IndexItem]) -> Dict:
        self.client.create_tables()
        self.client.write_index_item_batch(batch)
        # TODO return status to pass to update_progress on coordinator
        return {}

    def run(self):
        self.index_item_batch_ref = self.coordinator.get_to_write_batch.remote()
        while True:
            index_item_batch = ray.get(self.work_item_ref)
            if index_item_batch is None:
                # TODO sleep here for some time to avoid waisting CPU cycles?
                continue

            # schedule async fetching of next work item to enable compute pipelining
            self.index_item_batch_ref = self.coordinator.get_to_write_batch.remote()
            # work item is a batch of index items to write to DB
            write_status = self.write_batch(index_item_batch)
            # TODO do we call ray.get here?
            self.coordinator.update_progress(write_status).remote()


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def load_df(path: str) -> pd.DataFrame:
    return s3_utils.load_df(path)


# TODO set CPU=0, or add parallelism resource, set memory and object_store_memory
@ray.remote
def load_and_queue_df(path: str, queue: List):
    df = ray.get(load_df.remote(path))
    queue.append(df)


# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def calculate_meta(df: pd.DataFrame) -> IndexItem:
    # TODO
    return {}


# TODO add batching?
# TODO set CPU=0, set memory and object_store_memory
@ray.remote
def index_and_queue_df(df: pd.DataFrame, queue: List):
    index_item = ray.get(calculate_meta.remote(df))
    queue.append(index_item)


def generate_input_items() -> Generator[InputItemBatch, None, None]:
    batch = []
    for inv_df in s3_utils.inventory():
        for row in inv_df.itertuples():
            d_row = row._asdict()

            # TODO add size to input item
            size_kb = d_row['size']/1024.0
            input_item = parse_s3_key(d_row['key'])
            input_item['size_kb'] = size_kb
            batch.append(input_item)
            if len(batch) == INPUT_ITEM_BATCH_SIZE:
                yield batch
                batch = []

    if len(batch) != 0:
        # TODO indicate last batch
        yield batch


# TODO typing
# TODO util this
def parse_s3_key(key: str) -> Optional[Dict]:

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
    exchange = None
    instrument_type = None
    symbol = None
    quote = None
    base = None
    data_type = None
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
        'data_type': data_type,
        'exchange': exchange,
        'symbol': symbol,
        'instrument_type': instrument_type,
        'quote': quote,
        'base': base
    }

