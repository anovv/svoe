from dataclasses import dataclass
from typing import Dict, List

from featurizer.features.feature_tree.feature_tree import Feature
from simulation.models.instrument import Instrument


@dataclass
class DataStreamEvent:
    timestamp: float
    receipt_timestamp: float
    feature_values: Dict[Feature, Dict[str, float]]


class DataStreamGenerator:

    def next(self) -> DataStreamEvent:
        raise NotImplementedError

    def has_next(self) -> bool:
        raise NotImplementedError

    def get_cur_mid_prices(self) -> Dict[Instrument, float]:
        raise NotImplementedError

    @classmethod
    def split(cls, *args, **kwargs) -> List['DataStreamGenerator']:
        raise NotImplementedError
