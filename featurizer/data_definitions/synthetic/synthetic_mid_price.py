from typing import Dict, List

from pandas import DataFrame
from portion import Interval

from featurizer.blocks.blocks import BlockRangeMeta
from featurizer.data_definitions.data_definition import EventSchema
from featurizer.data_definitions.synthetic_data_source_definition import SyntheticDataSourceDefinition


class SyntheticMidPrice(SyntheticDataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'mid_price': float,
        }

    @classmethod
    def gen_synthetic_events(cls, interval: Interval, params: Dict) -> DataFrame:
        pass # TODO

    @classmethod
    def gen_synthetic_ranges_meta(cls, start_date: str, end_date: str) -> List[BlockRangeMeta]:
        pass # TODO