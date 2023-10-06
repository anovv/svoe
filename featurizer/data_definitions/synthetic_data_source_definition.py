from typing import List

from featurizer.blocks.blocks import BlockRangeMeta
from featurizer.data_definitions.data_definition import DataDefinition

# TODO explore https://stochastic.readthedocs.io/en/stable/
# TODO remove this and DataDefinition, keep only FeatureDefinition?
class SyntheticDataSourceDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return True

    @classmethod
    def is_synthetic(cls) -> bool:
        return True

    @classmethod
    def gen_synthetic_ranges_meta(cls, start_date: str, end_date: str, num_splits: int) -> List[BlockRangeMeta]:
        raise NotImplementedError
