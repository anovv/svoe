from typing import Optional, Dict, List

from data_catalog.utils.sql.client import MysqlClient

class Api:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)
# TODO should be synced with featurizer and indexer data models
# TODO typing
    def get_meta(
        self,
        exchange: str,
        data_type: str,
        instrument_type: str,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List:
        meta = self.client.select(exchange, data_type, instrument_type, symbol, start_date, end_date)
        ranges = self._make_ranges(meta)

    # TODO sync typing with featurizer
    # TODO this should be in utils classes for ranges?
    def _make_ranges(self, data: List) -> List[List]:
        # if conseq files differ no more than this, they are in the same range
        # TODO should this be const per data_type?
        SAME_RANGE_DIFF_S = 1
        res = []
        cur_range = []
        for i in range(len(data)):
            if i == len(data) - 1:
                res.append(data[i])
                continue
            if float(data[i + 1]['start_ts']) - float(data[i]['end_ts']) > SAME_RANGE_DIFF_S:
                # TODO finish this
                pass

        return []


