import logging
from typing import List, Optional

from svoe.featurizer_v2.streaming.runtime.transfer.channel import Channel, ChannelMessage
from svoe.featurizer_v2.streaming.runtime.transfer.data_writer import TransportType

import zmq
import json


logger = logging.getLogger("ray")

class DataReader:
    def __init__(
        self,
        input_channels: List[Channel],
        transport_type: TransportType = TransportType.ZMQ_PUSH_PULL
    ):
        if transport_type not in [
            TransportType.ZMQ_PUSH_PULL,
        ]:
            raise RuntimeError(f'Unsupported transport {transport_type}')

        self.input_channels = input_channels

        self.cur_read_id = 0

        # TODO buffering
        self.sockets_and_contexts = {}
        for channel in self.input_channels:
            context = zmq.Context()
            # TODO set HWM
            socket = context.socket(zmq.PULL)
            socket.connect(f'tcp://{channel.source_ip}:{channel.source_port}')
            self.sockets_and_contexts[channel.channel_id] = (socket, context)

    # TODO set timeout
    def read_message(self) -> Optional[ChannelMessage]:
        # TODO this should use a buffer?

        # round robin read
        channel_id = self.input_channels[self.cur_read_id].channel_id
        socket = self.sockets_and_contexts[channel_id][0]
        try:
            json_str = socket.recv_string()
        except zmq.error.ContextTerminated:
            logger.info('zmq recv interrupt due to ContextTerminated')
            return None
        self.cur_read_id = (self.cur_read_id + 1)%len(self.input_channels)

        # TODO serialization perf
        return json.loads(json_str)

    def close(self):
        # cleanup sockets and contexts for all channels
        for channel_id in self.sockets_and_contexts:
            socket = self.sockets_and_contexts[channel_id][0]
            context = self.sockets_and_contexts[channel_id][1]
            socket.setsockopt(zmq.LINGER, 0)
            socket.close()
            context.destroy()