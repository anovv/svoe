from typing import List, Union, Dict, Optional

import ciso8601
from pydantic import BaseModel

import yaml

from common.time.utils import split_time_range_between_ts, ts_to_str_date


class FeatureConfig(BaseModel):
    feature_definition: str
    params: Dict
    name: Optional[str] = None
    deps: Optional[List[str]] = None


class FeaturizerConfig(BaseModel):
    feature_configs: List[FeatureConfig]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    label_lookahead: Optional[str] = None
    label_feature: Optional[Union[int, str]] = None
    features_to_store: Optional[List[int]] = []

    @classmethod
    def load_config(cls, path: str) -> 'FeaturizerConfig':
        with open(path, 'r') as stream:
            d = yaml.safe_load(stream)
            return FeaturizerConfig.parse_obj(d)


def split_featurizer_config(featurizer_config: FeaturizerConfig, num_splits: int) -> List[FeaturizerConfig]:
    start_date = featurizer_config.start_date
    end_date = featurizer_config.end_date
    splits = []
    start_ts = ciso8601.parse_datetime(start_date).timestamp()
    end_ts = ciso8601.parse_datetime(end_date).timestamp()
    split_ranges = split_time_range_between_ts(start_ts, end_ts, num_splits, 0.1)
    date_range_splits = [(ts_to_str_date(i.lower), ts_to_str_date(i.upper)) for i in split_ranges]

    for _start_date, _end_date in date_range_splits:
        config_split = featurizer_config.copy(deep=True)
        config_split.start_date = _start_date
        config_split.end_date = _end_date
        splits.append(config_split)

    return splits


