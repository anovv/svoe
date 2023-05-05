from typing import Optional, Dict, List, Tuple

from featurizer.blocks.blocks import BlockRangeMeta, make_ranges
from featurizer.data_catalog.common.utils.sql.client import MysqlClient
from featurizer.data_catalog.common.utils.sql.models import DataCatalog

# TODO this should be synced with DataDef somehow?
GroupKey = Tuple[str, str, str, str]


def group_key(e) -> GroupKey:
    return (e[DataCatalog.exchange.name], e[DataCatalog.data_type.name], e[DataCatalog.instrument_type.name],
            e[DataCatalog.symbol.name])


class Api:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    # TODO should be synced with featurizer data models
    # TODO typing
    def get_meta(
        self,
        exchanges: List[str],
        data_types:List[str],
        instrument_types: List[str],
        symbols: [str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[GroupKey, List[BlockRangeMeta]]:
        raw_data = self.client.select(exchanges, data_types, instrument_types, symbols, start_date, end_date)

        # group data
        groups = {}
        for r in raw_data:
            key = group_key(r)
            if key in groups:
                groups[key].append(r)
            else:
                groups[key] = [r]

        # for k in groups:
        #     groups[k] = make_ranges(groups[k])

        return groups
