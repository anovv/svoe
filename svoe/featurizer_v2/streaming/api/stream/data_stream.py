from typing import List, Callable

from svoe.featurizer_v2.streaming.api.function.function import KeyFunction, SimpleMapFunction, SimpleFlatMapFunction, \
    SimpleFilterFunction, SimpleKeyFunction, SimpleJoinFunction, SimpleReduceFunction, SimpleSinkFunction
from svoe.featurizer_v2.streaming.api.operator.operator import MapOperator, FlatMapOperator, FilterOperator, \
    ReduceOperator, StreamOperator, JoinOperator, KeyByOperator, SinkOperator
from svoe.featurizer_v2.streaming.api.partition.partition import KeyPartition
from svoe.featurizer_v2.streaming.api.stream.stream import Stream
from svoe.featurizer_v2.streaming.api.stream.stream_sink import StreamSink


class DataStream(Stream):

    def map(self, map_func_callable: Callable) -> 'DataStream':
        map_func = SimpleMapFunction(map_func_callable)
        return DataStream(
            input_stream=self,
            stream_operator=MapOperator(map_func),
        )

    def flat_map(self, flat_map_func_callable: Callable) -> 'DataStream':
        flat_map_func = SimpleFlatMapFunction(flat_map_func_callable)
        return DataStream(
            input_stream=self,
            stream_operator=FlatMapOperator(flat_map_func),
        )

    def filter(self, filter_func_callable: Callable) -> 'DataStream':
        filter_func = SimpleFilterFunction(filter_func_callable)
        return DataStream(
            input_stream=self,
            stream_operator=FilterOperator(filter_func),
        )

    def join(self, other: 'DataStream') -> 'JoinStream':
        return JoinStream(
            left_stream=self,
            right_stream=other
        )

    def key_by(self, key_by_func_callable: Callable) -> 'KeyDataStream':
        key_by_func = SimpleKeyFunction(key_by_func_callable)
        return KeyDataStream(
            input_stream=self,
            stream_operator=KeyByOperator(key_by_func)
        )

    def sink(self, sink_func_callable: Callable) -> 'StreamSink':
        sink_func = SimpleSinkFunction(sink_func_callable)
        return StreamSink(
            input_stream=self,
            sink_operator=SinkOperator(sink_func)
        )

    # TODO union, broadcast, partition_by, process
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

    def where_key(self, key_by_func_callable: Callable) -> 'JoinWhere':
        self.stream_operator.left_key_by_function = SimpleKeyFunction(key_by_func_callable)
        return JoinWhere(join_stream=self)


class JoinEqual:

    def __init__(
        self,
        join_stream: 'JoinStream'
    ):
        self.join_stream = join_stream

    def with_func(self, join_func_callable: Callable) -> DataStream:
        self.join_stream.stream_operator.func = SimpleJoinFunction(join_func_callable)
        return self.join_stream


class JoinWhere:

    def __init__(
        self,
        join_stream: 'JoinStream'
    ):
        self.join_stream = join_stream

    def equal_to(self, right_key_by_func_callable: callable) -> JoinEqual:
        self.join_stream.stream_operator.right_key_by_function = SimpleKeyFunction(right_key_by_func_callable)
        return JoinEqual(self.join_stream)


# key_by
class KeyDataStream(DataStream):

    def __init__(
        self,
        input_stream: Stream,
        stream_operator: StreamOperator
    ):
        super().__init__(input_stream=input_stream, stream_operator=stream_operator, partition=KeyPartition())

    def reduce(self, reduce_func_callable: Callable) -> DataStream:
        reduce_function = SimpleReduceFunction(reduce_func_callable)
        return DataStream(input_stream=self, stream_operator=ReduceOperator(reduce_function))

    def aggregate(self) -> DataStream:
        # TODO implement keyed aggregation
        raise NotImplementedError


# union
class UnionStream(DataStream):

    def __init__(self, streams: List[Stream]):
        # TODO call super
        self.union_streams = streams
