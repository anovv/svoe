from typing import Callable


class DataSourceEventEmitter:

    # TODO callback typing, add event type
    def __init__(self, callback: Callable):
        self.callback = callback

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
