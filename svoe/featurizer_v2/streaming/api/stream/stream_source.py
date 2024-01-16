from svoe.featurizer_v2.streaming.api.function.function import SourceFunction
from svoe.featurizer_v2.streaming.api.operator.operator import SourceOperator
from svoe.featurizer_v2.streaming.api.stream.data_stream import DataStream


class StreamSource(DataStream):

    def __init__(self, streaming_context: 'StreamingContext', source_function: SourceFunction):
        super().__init__(
            streaming_context=streaming_context,
            stream_operator=SourceOperator(source_function)
        )