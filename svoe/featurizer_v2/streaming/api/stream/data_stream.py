from typing import List

from svoe.featurizer_v2.streaming.api.function.function import MapFunction, FlatMapFunction, FilterFunction
from svoe.featurizer_v2.streaming.api.operator.operator import MapOperator, FlatMapOperator, FilterOperator
from svoe.featurizer_v2.streaming.api.stream.stream import Stream


class DataStream(Stream):

    def map(self, map_func: MapFunction) -> 'DataStream':
        return DataStream(
            input_stream=self,
            stream_operator=MapOperator(map_func),
        )

    def flat_map(self, flat_map_func: FlatMapFunction) -> 'DataStream':
        return DataStream(
            input_stream=self,
            stream_operator=FlatMapOperator(flat_map_func),
        )

    def filter(self, filter_func: FilterFunction) -> 'DataStream':
        return DataStream(
            input_stream=self,
            stream_operator=FilterOperator(filter_func),
        )

    # TODO join, union, key_by
    # def union(self, streams: List[Stream]) -> 'DataStream':

