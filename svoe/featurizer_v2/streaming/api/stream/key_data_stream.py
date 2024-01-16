from svoe.featurizer_v2.streaming.api.function.function import ReduceFunction
from svoe.featurizer_v2.streaming.api.operator.operator import StreamOperator, ReduceOperator
from svoe.featurizer_v2.streaming.api.stream.data_stream import DataStream
from svoe.featurizer_v2.streaming.api.stream.stream import Stream


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