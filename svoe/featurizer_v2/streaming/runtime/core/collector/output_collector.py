from typing import List

from svoe.featurizer_v2.streaming.api.collector.collector import Collector
from svoe.featurizer_v2.streaming.api.message.message import Record
from svoe.featurizer_v2.streaming.api.partition.partition import Partition
from svoe.featurizer_v2.streaming.runtime.transfer.data_writer import DataWriter


class OutputCollector(Collector):

    def __init__(
        self,
        data_writer: DataWriter,
        output_channel_ids: List[str],
        partition: Partition
    ):
        self.data_writer = data_writer
        self.output_channel_ids = output_channel_ids
        self.partition = partition

    def collect(self, record: Record):
        partitions = self.partition.partition(record=record, num_partition=len(self.output_channel_ids))
        for partition in partitions:
            self.data_writer.write_message(self.output_channel_ids[partition], record.to_channel_message())
