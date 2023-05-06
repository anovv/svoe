
from portion import Interval, closed, IntervalDict

from typing import Optional, Dict, List, Tuple

from featurizer.blocks.blocks import BlockRangeMeta, make_ranges, prune_overlaps, get_overlaps
from featurizer.data_catalog.common.sql.client import MysqlClient
from featurizer.data_catalog.common.sql.models import DataCatalog

# TODO this should be synced with DataDef somehow?
DataKey = Tuple[str, str, str, str]


def data_key(e: Dict) -> DataKey:
    return (e[DataCatalog.exchange.name], e[DataCatalog.data_type.name], e[DataCatalog.instrument_type.name],
            e[DataCatalog.symbol.name])


class Api:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    def get_meta_from_data_keys(
        self,
        data_keys: List[DataKey],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[Interval, Dict[DataKey, List[BlockRangeMeta]]]:
        exchanges = [d[0] for d in data_keys]
        data_types = [d[0] for d in data_keys]
        instrument_types = [d[0] for d in data_keys]
        symbols = [d[0] for d in data_keys]
        return self.get_meta(exchanges, data_types, instrument_types, symbols, start_date, end_date)

    def get_meta(
        self,
        exchanges: List[str],
        data_types: List[str],
        instrument_types: List[str],
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[Interval, Dict[DataKey, List[BlockRangeMeta]]]:
        raw_data = self.client.select(exchanges, data_types, instrument_types, symbols, start_date, end_date)

        # group data by data key
        groups = {}
        for r in raw_data:
            key = data_key(r)
            if key in groups:
                groups[key].append(r)
            else:
                groups[key] = [r]

        # make overlaps
        grouped_ranges = {}
        for k in groups:
            ranges = make_ranges(groups[k])
            ranges_dict = IntervalDict()
            for r in ranges:
                start_ts = r[0][DataCatalog.start_ts.name]
                end_ts = r[-1][DataCatalog.end_ts.name]
                ranges_dict[closed(start_ts, end_ts)] = r
            grouped_ranges[k] = ranges_dict

        overlaped_ranges = prune_overlaps(get_overlaps(grouped_ranges))
        # validate result
        prev = None
        keys = None
        for interval in overlaped_ranges:
            # validate overlaps are sorted
            if prev is None:
                prev = interval
            else:
                if prev.upper > interval.lower:
                    raise ValueError(f'Overlaps are not sorted')

            # validate each group has same keys
            if keys is None:
                keys = overlaped_ranges[interval].keys()
            else:
                if keys != overlaped_ranges[interval].keys():
                    raise ValueError(f'Keys are not the same, expected: {keys} got {overlaped_ranges[interval]}')

        return overlaped_ranges
