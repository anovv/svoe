from typing import List

from svoe.featurizer_v2.streaming.api.function.function import MapFunction, FlatMapFunction, FilterFunction, \
    JoinFunction
from svoe.featurizer_v2.streaming.api.operator.operator import MapOperator, FlatMapOperator, FilterOperator
from svoe.featurizer_v2.streaming.api.stream.join_stream import JoinStream
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

    def join(self, other: 'DataStream') -> JoinStream:
        return JoinStream(
            left_stream=self,
            right_stream=other
        )

    # def key_by(self):

    # TODO sink, key_by, union, broadcast, partition_by, process
    # def union(self, streams: List[Stream]) -> 'DataStream':



