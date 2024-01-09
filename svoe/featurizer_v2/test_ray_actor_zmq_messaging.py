import time
import random
from socket import socket

import ray
import zmq


@ray.remote
class Pub:

    def __init__(self):
        self.port = None
        self.socket = None

    def initialize(self, port: int):
        self.port = port
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind(f'tcp://127.0.0.1:{port}')
        pass

    def start(self):
        while True:
            topic = random.randrange(10000, 10002)
            messagedata = random.randrange(1, 215) - 80
            self.socket.send_string("%d %d" % (topic, messagedata))
            time.sleep(1)

@ray.remote
class Sub:
    def __init__(self):
        self.port = None
        self.socket = None

    def initialize(self, producer_addr: str):
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect(producer_addr)

    def start(self):
        topicfilter = '10001'
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topicfilter)

        # Process 5 updates
        total_value = 0
        while True:
            string = self.socket.recv()
            topic, messagedata = string.split()
            total_value += int(messagedata)
            print(topic, messagedata)

with ray.init(address='auto'):
    pub_port = 5151
    pub_addr = f'tcp://127.0.0.1:{pub_port}'
    pub = Pub.remote()
    ray.get(pub.initialize.remote(pub_port))
    sub = Sub.remote()
    ray.get(sub.initialize.remote(pub_addr))
    pub.start.remote()
    ray.get(sub.start.remote())
