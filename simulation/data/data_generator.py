from typing import Dict

from simulation.events.events import DataEvent


class DataGenerator:

    def __init__(self, config: Dict):
        self.config = config
        # TODO fetch data from remote storage based on config and queue it

    def next(self) -> DataEvent:
        raise # TODO

    def should_stop(self) -> bool:
        raise # TODO