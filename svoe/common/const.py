import os
from enum import Enum

DEFAULT_LOCAL_RAY_ADDRESS = 'ray://127.0.0.1:10001' # TODO read env var

NUM_CPUS = os.cpu_count()

class Fields(str, Enum):
    EXCHANGE = 'exchange'
    DATA_TYPE = 'data_type'
    INSTRUMENT_TYPE = 'instrument_type'
    SYMBOL = 'symbol'
    QUOTE = 'quote'
    BASE = 'base'
    PATH = 'path'
    SOURCE = 'source'