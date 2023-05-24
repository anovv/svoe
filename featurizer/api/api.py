
from portion import Interval, closed, IntervalDict

from typing import Optional, Dict, List, Tuple

from featurizer.blocks.blocks import BlockRangeMeta, make_ranges, prune_overlaps, get_overlaps, ranges_to_interval_dict, \
    BlockMeta
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.sql.client import MysqlClient
from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.sql.feature_catalog.models import FeatureCatalog

# TODO this should be synced with DataDef somehow?
DataKey = Tuple[str, str, str, str]


def data_key(e: Dict) -> DataKey:
    return (e[DataCatalog.exchange.name], e[DataCatalog.data_type.name], e[DataCatalog.instrument_type.name],
            e[DataCatalog.symbol.name])


class Api:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)

    def get_data_meta(
        self,
        data_keys: List[DataKey], # TODO make it Feature objects and derive keys
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[DataKey, List[BlockRangeMeta]]:
        exchanges = [d[0] for d in data_keys]
        data_types = [d[1] for d in data_keys]
        instrument_types = [d[2] for d in data_keys]
        symbols = [d[3] for d in data_keys]
        return self._get_data_meta(exchanges, data_types, instrument_types, symbols, start_date=start_date, end_date=end_date)

    def _get_data_meta(
        self,
        exchanges: List[str],
        data_types: List[str],
        instrument_types: List[str],
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[DataKey, List[BlockRangeMeta]]:
        raw_data = self.client.select_data_catalog(exchanges, data_types, instrument_types, symbols, start_date=start_date, end_date=end_date)
        raw_data = raw_data[:10] # TODO this is for debug
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
            grouped_ranges[k] = ranges
        return grouped_ranges

    def get_features_meta(
        self,
        features: List[Feature],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[Feature, Dict[Interval, BlockMeta]]: # TODO return FeatureCatalog instead of Dict?
        feature_keys = [f.feature_key for f in features]
        raw_data = self.client.select_feature_catalog(feature_keys, start_date=start_date, end_date=end_date)
        groups = {}

        def _feature_by_key(key):
            for f in features:
                if f.feature_key == key:
                    return f
            return None

        for r in raw_data:
            feature_key = r[FeatureCatalog.feature_key.name]
            start_ts = float(r[FeatureCatalog.start_ts.name])
            end_ts = float(r[FeatureCatalog.end_ts.name])
            interval = closed(start_ts, end_ts)
            feature = _feature_by_key(feature_key)
            if feature in groups:
                if interval in groups[feature]:
                    raise ValueError('FeatureCatalog entry duplicate interval')
                groups[feature][interval] = r
            else:
                groups[feature] = {interval: r}

        return groups