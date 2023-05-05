import asyncio
import logging
import os
import zmq
import zmq.asyncio


from featurizer.featurizer.log import get_logger
from featurizer.featurizer.util import get_queue_key
from featurizer.featurizer.calculator import Calculator
from faster_fifo import Queue

LOG = get_logger('featurizer', 'featurizer.log', logging.INFO, size=50000000, num_files=10)


# https://github.com/alex-petrenko/faster-fifo high perf multiproc queue
class Featurizer:

    def __init__(self, config_path: str):
        self.config = self._read_config(config_path) # TODO use DynamicConfig?
        self.queues = self._init_queues()
        self.calculator = Calculator(self.config, self.queues)
        ctx = zmq.asyncio.Context.instance()
        # self.in_sockets = []
        self.poller = zmq.asyncio.Poller()
        addresses = self._get_addresses()
        for address in addresses:
            socket = ctx.socket(zmq.SUB)
            socket.connect(address)
            self.poller.register(socket, zmq.POLLIN)

    def run(self):
        LOG.info("Featurizer running on PID %d", os.getpid())
        self.calculator.start()
        loop = asyncio.get_event_loop()
        loop.create_task(self.loop())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        except Exception:
            LOG.error("Featurizer running on PID %d died due to exception", os.getpid(), exc_info=True)

    async def loop(self):
        while True: # TODO add interrupt handlers
            try:
                events = await self.poller.poll()
                for socket in dict(events):
                    msg = await socket.recv_string()
                    self._handle_message(msg)

            except Exception:
                LOG.error("Featurizer running on PID %d died due to exception", os.getpid(), exc_info=True)
                raise

    @staticmethod
    def _read_config(config_path: str) -> dict:
        # TODO
        return {}

    def _get_addresses(self) -> list:
        return self.config['addresses']

    def _init_queues(self) -> dict:
        queues = {} # no need for shared multiproc dict as it is read-only
        exchanges = self.config['exchanges']
        for exchange in exchanges:
            for data_type in exchange:
                for symbol in exchange[data_type]:
                    queues[get_queue_key(exchange, data_type, symbol)] = Queue()
        return queues

    def _handle_message(self, msg: str):
        exchange, data_type, symbol, data = self._parse_message(msg)
        key = get_queue_key(exchange, data_type, symbol)
        if key in self.queues: # TODO log dropped messages?
            self.queues[key].put(data)

    @staticmethod
    def _parse_message(msg: str) -> tuple:
        return None  # TODO
