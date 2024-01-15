from typing import List

from svoe.featurizer_v2.streaming.api.stream.data_stream import DataStream
from svoe.featurizer_v2.streaming.api.stream.stream import Stream


class UnionStream(DataStream):

    def __init__(self, streams: List[Stream]):
        # TODO call super
        self.union_streams = streams