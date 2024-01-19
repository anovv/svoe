from abc import ABC, abstractmethod
from typing import List

from svoe.featurizer_v2.streaming.api.collector.collector import Collector
from svoe.featurizer_v2.streaming.api.context.runtime_context import RuntimeContext
from svoe.featurizer_v2.streaming.api.message.message import Record
from svoe.featurizer_v2.streaming.api.operator.operator import OneInputOperator, Operator, SourceOperator, \
    StreamOperator, OperatorType


class Processor(ABC):

    @abstractmethod
    def open(self, collectors: List[Collector], runtime_context: RuntimeContext):
        pass

    @abstractmethod
    def process(self, record: Record):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def finish(self):
        pass

    @classmethod
    def build_processor(cls, stream_operator: StreamOperator) -> 'StreamProcessor':
        op_type = stream_operator.operator_type()
        if op_type == OperatorType.SOURCE:
            return SourceProcessor(stream_operator)
        elif op_type == OperatorType.ONE_INPUT:
            return OneInputProcessor(stream_operator)
        elif op_type == OperatorType.TWO_INPUT:
            return TwoInputProcessor(stream_operator)
        else:
            raise RuntimeError('Unsupported operator type')


class StreamProcessor(Processor, ABC):

    def __init__(self, operator: Operator):
        self.operator = operator
        self.collectors = None
        self.runtime_context = None

    def open(self, collectors: List[Collector], runtime_context: RuntimeContext):
        self.collectors = collectors
        self.runtime_context = runtime_context
        self.operator.open(collectors=collectors, runtime_context=runtime_context)

    def close(self):
        self.operator.close()

    def finish(self):
        self.operator.finish()


class OneInputProcessor(StreamProcessor):
    def __init__(self, one_input_operator: OneInputOperator):
        super().__init__(operator=one_input_operator)

    def process(self, record: Record):
        self.operator.process_element(record)


class TwoInputProcessor(StreamProcessor):
    def __init__(self, two_input_operator: OneInputOperator):
        super().__init__(operator=two_input_operator)
        self.left_stream_name = None
        self.right_stream_name = None

    def process(self, record: Record):
        stream_name = record.stream_name
        if self.left_stream_name == stream_name:
            self.operator.process_element(record, None)
        elif self.right_stream_name == stream_name:
            self.operator.process_element(None, record)


class SourceProcessor(StreamProcessor):
    def __init__(self, source_operator: SourceOperator):
        super().__init__(operator=source_operator)

    def process(self, record: Record):
        self.operator.fetch()
