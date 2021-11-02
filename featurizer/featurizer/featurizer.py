import logging
import os

from featurizer.featurizer.log import get_logger

LOG = get_logger('cryptostore', 'cryptostore.log', logging.INFO, size=50000000, num_files=10)

class Featurizer:

    def __init__(self, config_path: str):
        self.config = self._read_config(config_path)

    def run(self):
        LOG.info("Starting featurizer")
        LOG.info("Featurizer running on PID %d", os.getpid())

        return

    @staticmethod
    def _read_config(config_path: str) -> dict:
        # TODO
        return {}