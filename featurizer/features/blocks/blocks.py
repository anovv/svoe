from typing import Dict, List
import pandas as pd
from portion import Interval, closed

# TODO merge all this with catalog methods
# catalog methods
BlockMeta = Dict # TODO represents s3 file metadata: name, time range, size, etc.
def get_interval(meta: BlockMeta) -> Interval:
    return closed(meta['start_ts'], meta['end_ts'])

BlockRangeMeta = List[BlockMeta] # represents metadata of consecutive blocks

# TODO typdef List[BlockRangeMeta]?

Block = pd.DataFrame
BlockRange = List[Block] # represents consecutive blocks

# TODO make abstraction for users to define data params for each input data channel
DataParams = Dict[str, Dict]