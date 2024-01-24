import logging
import time
from abc import ABC, abstractmethod
from threading import Thread

from svoe.featurizer_v2.streaming.api.job_graph.job_graph import VertexType
from svoe.featurizer_v2.streaming.api.message.message import Record, record_from_channel_message
from svoe.featurizer_v2.streaming.runtime.core.execution_graph.execution_graph import ExecutionVertex
from svoe.featurizer_v2.streaming.runtime.worker.task.streaming_runtime_context import StreamingRuntimeContext
from svoe.featurizer_v2.streaming.runtime.core.collector.output_collector import OutputCollector
from svoe.featurizer_v2.streaming.runtime.core.processor.processor import Processor, TwoInputProcessor
from svoe.featurizer_v2.streaming.runtime.transfer.data_reader import DataReader
from svoe.featurizer_v2.streaming.runtime.transfer.data_writer import DataWriter


logger = logging.getLogger("ray")


class StreamTask(ABC):

    def __init__(
        self,
        processor: Processor,
        execution_vertex: ExecutionVertex
    ):
        self.processor = processor
        self.execution_vertex = execution_vertex
        self.thread = Thread(target=self.run, daemon=True)
        self.writer = None
        self.reader = None
        self.running = True
        self.collectors = []

    @abstractmethod
    def run(self):
        pass

    def start_or_recover(self):
        self._prepare_task()
        self.thread.start()

    def _prepare_task(self):
        # writer
        if len(self.execution_vertex.output_edges) != 0:
            output_channels = self.execution_vertex.get_output_channels()
            assert len(output_channels) > 0
            assert output_channels[0] != None
            if self.writer != None:
                raise RuntimeError('Writer already inited')
            if self.execution_vertex.job_vertex.vertex_type != VertexType.SINK:
                # sinks do not pass data downstream so no writer
                self.writer = DataWriter(
                    source_stream_name=str(self.execution_vertex.stream_operator.id),
                    output_channels=output_channels
                )

        # reader
        if len(self.execution_vertex.input_edges) != 0:
            input_channels = self.execution_vertex.get_input_channels()
            assert len(input_channels) > 0
            assert input_channels[0] != None
            if self.reader != None:
                raise RuntimeError('Reader already inited')
            if self.execution_vertex.job_vertex.vertex_type != VertexType.SOURCE:
                # sources do not read data from upstream so no reader
                self.reader = DataReader(
                    input_channels=input_channels
                )

        self._open_processor()

    def _open_processor(self):
        execution_vertex = self.execution_vertex
        output_edges = execution_vertex.output_edges
        # grouped by each operator in target vertex
        grouped_channel_ids = {}
        grouped_partitions = {}

        for i in range(len(output_edges)):
            output_edge = output_edges[i]
            op_name = output_edge.target_execution_vertex.job_vertex.get_name()
            if op_name not in grouped_channel_ids:
                grouped_channel_ids[op_name] = []
            output_channel_ids = [ch.channel_id for ch in execution_vertex.get_output_channels()]
            grouped_channel_ids[op_name].append(output_channel_ids[i])
            grouped_partitions[op_name] = output_edge.partition

        for op_name in grouped_partitions:
            self.collectors.append(OutputCollector(
                data_writer=self.writer,
                output_channel_ids=grouped_channel_ids[op_name],
                partition=grouped_partitions[op_name]
            ))

        runtime_context = StreamingRuntimeContext(execution_vertex=execution_vertex)

        self.processor.open(
            collectors=self.collectors,
            runtime_context=runtime_context
        )

    def close(self):
        logger.info(f'Closing task {self.execution_vertex.execution_vertex_id}...')
        self.running = False
        self.processor.close()
        if self.writer != None:
            self.writer.close()
            logger.info(f'Closed writer for task {self.execution_vertex.execution_vertex_id}')

        if self.reader != None:
            self.reader.close()
            logger.info(f'Closed reader for task {self.execution_vertex.execution_vertex_id}')
        self.thread.join(timeout=5)
        logger.info(f'Closed task {self.execution_vertex.execution_vertex_id}')


class SourceStreamTask(StreamTask):

    def run(self):
        while self.running:
            record = Record(value=None) # empty message, this will trigger sourceFunction.fetch()
            self.processor.process(record)


class InputStreamTask(StreamTask):

    def run(self):
        while self.running:
            message = self.reader.read_message()
            if message is None:
                # TODO indicate special message
                continue
            record = record_from_channel_message(message)
            # if isinstance(self.execution_vertex.stream_operator, JoinOperator):
            #     print(record)
            self.processor.process(record)


class OneInputStreamTask(InputStreamTask):
    pass


class TwoInputStreamTask(InputStreamTask):

    def __init__(
        self,
        processor: Processor,
        execution_vertex: ExecutionVertex,
        left_stream_name: str,
        right_stream_name: str,
    ):
        super().__init__(
            processor=processor,
            execution_vertex=execution_vertex
        )

        assert isinstance(self.processor, TwoInputProcessor)
        self.processor.left_stream_name = left_stream_name
        self.processor.right_stream_name = right_stream_name

