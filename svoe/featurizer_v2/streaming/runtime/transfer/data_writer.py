import enum
import json
from typing import List, Any, Dict

from svoe.featurizer_v2.streaming.runtime.transfer.channel import Channel

import zmq


class TransportType(enum.Enum):
    ZMQ_PUSH_PULL = 1
    ZMQ_PUB_SUB = 2
    RAY_SHARED_MEM = 3


class DataWriter:

    def __init__(
        self,
        out_channels: List[Channel],
        transport_type: TransportType = TransportType.ZMQ_PUSH_PULL
    ):
        if transport_type not in [
            TransportType.ZMQ_PUSH_PULL,
        ]:
            raise RuntimeError(f'Unsupported transport {transport_type}')

        self.out_channels = out_channels

        # TODO buffering

        self.sockets = {}
        for channel in self.out_channels:
            if channel.channel_id in self.sockets:
                raise RuntimeError('duplicate channel ids')
            context = zmq.Context()

            # TODO set HWM
            socket = context.socket(zmq.PUSH)
            socket.bind(f'tcp://127.0.0.1:{channel.source_port}')
            self.sockets[channel.channel_id] = socket

    def write_message(self, channel_id: str, message_dict: Dict):
        # TODO this should use a buffer?

        # TODO serialization perf
        json_str = json.dumps(message_dict)

        # TODO depends on socket type, this can block or just throw exception, test this
        self.sockets[channel_id].send_string(json_str)