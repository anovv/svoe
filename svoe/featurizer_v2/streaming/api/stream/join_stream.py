from svoe.featurizer_v2.streaming.api.function.function import JoinFunction, KeyFunction
from svoe.featurizer_v2.streaming.api.operator.operator import JoinOperator
from svoe.featurizer_v2.streaming.api.stream.data_stream import DataStream


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
