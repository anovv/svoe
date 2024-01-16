from typing import List

from svoe.featurizer_v2.streaming.api.function.function import MapFunction, FlatMapFunction, FilterFunction, \
    JoinFunction, ReduceFunction, KeyFunction
from svoe.featurizer_v2.streaming.api.operator.operator import MapOperator, FlatMapOperator, FilterOperator, \
    ReduceOperator, StreamOperator, JoinOperator
# from svoe.featurizer_v2.streaming.api.stream.join_stream import JoinStream
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

    def join(self, other: 'DataStream') -> 'JoinStream':
        return JoinStream(
            left_stream=self,
            right_stream=other
        )

    # def key_by(self):

    # TODO sink, key_by, union, broadcast, partition_by, process
    # def union(self, streams: List[Stream]) -> 'DataStream':



# join
class JoinStream(DataStream):

    def __init__(
        self,
        left_stream: DataStream,
        right_stream: DataStream,
    ):
        super().__init__(input_stream=left_stream, stream_operator=JoinOperator())
        self.right_stream = right_stream

    def where_key(self, key_by_func: KeyFunction) -> 'JoinWhere':
        return JoinWhere(
            join_stream=self,
            left_key_by_func=key_by_func
        )


class JoinEqual:

    def __init__(
        self,
        join_stream: 'JoinStream',
        left_key_by_func: KeyFunction,
        right_key_by_func: KeyFunction
    ):
        self.join_stream = join_stream
        self.left_key_by_func = left_key_by_func
        self.right_key_by_func = right_key_by_func

    def with_func(self, join_func: JoinFunction) -> DataStream:
        join_operator = self.join_stream.stream_operator
        join_operator.func = join_func
        return self.join_stream


class JoinWhere:

    def __init__(
        self,
        join_stream: 'JoinStream',
        left_key_by_func: KeyFunction
    ):
        self.join_stream = join_stream
        self.left_key_by_func = left_key_by_func

    def equal_to(self, right_key_by_func: KeyFunction) -> JoinEqual:
        return JoinEqual(self.join_stream, self.left_key_by_func, right_key_by_func)

# key_by
class KeyDataStream(DataStream):

    def __init__(
        self,
        input_stream: Stream,
        stream_operator: StreamOperator
    ):
        super().__init__(input_stream=input_stream, stream_operator=stream_operator)

    def reduce(self, reduce_function: ReduceFunction) -> DataStream:
        return DataStream(input_stream=self, stream_operator=ReduceOperator(reduce_function))

    def aggregate(self) -> DataStream:
        # TODO implement keyed aggregation
        raise NotImplementedError

# union
class UnionStream(DataStream):

    def __init__(self, streams: List[Stream]):
        # TODO call super
        self.union_streams = streams
