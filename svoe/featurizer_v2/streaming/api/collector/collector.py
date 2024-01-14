import logging
from abc import ABC, abstractmethod

from svoe.featurizer_v2.streaming.api.message.message import Record

logger = logging.getLogger(__name__)


class Collector(ABC):
    # Collects data from an upstream operator and emits to downstream operators

    @abstractmethod
    def collect(self, record):
        pass


class CollectionCollector(Collector):
    def __init__(self, collector_list):
        self._collector_list = collector_list

    def collect(self, value):
        for collector in self._collector_list:
            collector.collect(Record(value))


class OutputCollector(Collector):
    # TODO
    pass