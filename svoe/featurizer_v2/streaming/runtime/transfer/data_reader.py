from typing import List, Dict

from svoe.featurizer_v2.streaming.runtime.transfer.channel import Channel
from svoe.featurizer_v2.streaming.runtime.transfer.data_writer import TransportType

import zmq
import json


class DataReader:
    def __init__(
        self,
        in_channels: List[Channel],
        transport_type: TransportType = TransportType.ZMQ_PUSH_PULL
    ):
        if transport_type not in [
            TransportType.ZMQ_PUSH_PULL,
        ]:
            raise RuntimeError(f'Unsupported transport {transport_type}')

        self.in_channels = in_channels

        self.cur_read_id = 0

        # TODO buffering

        self.sockets = []
        for channel in self.in_channels:
            context = zmq.Context()

            # TODO set HWM
            socket = context.socket(zmq.PULL)
            socket.connect(f'tcp://{channel.source_ip}:{channel.source_port}')
            self.sockets.append(socket)

    # TODO set timeout
    def read_message(self) -> Dict:
        # TODO this should use a buffer?

        # round robin read
        json_str = self.sockets[self.cur_read_id].recv_string()
        self.cur_read_id = (self.cur_read_id + 1)%len(self.sockets)

        # TODO serialization perf
        return json.loads(json_str)