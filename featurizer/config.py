from typing import List, Union, Dict, Optional

from pydantic import BaseModel
from pydantic_yaml import YamlModelMixin


class FeatureConfig(BaseModel):
    feature_definition: str
    data_params: Union[List[Dict], Dict]
    feature_params: Union[List[Dict], Dict]


class FeaturizerConfig(BaseModel, YamlModelMixin):
    feature_configs: List[FeatureConfig]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    join: Optional[bool] = True
    lookahead_shift: Optional[str] = None
    label_feature: Optional[str] = None
    feature_to_store: Optional[List[str]] = []

    @classmethod
    def load_config(cls, path: str) -> 'FeaturizerConfig':
        return FeaturizerConfig.parse_file(path=path)

