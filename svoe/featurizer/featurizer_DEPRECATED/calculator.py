import logging
import os
from multiprocessing import Process
from svoe.featurizer import get_logger

LOG = get_logger('featurizer', 'featurizer.log', logging.INFO, size=50000000, num_files=10)


class Calculator(Process):

    # TODO use pool of processes instead of a single process?
    def __init__(self, config: dict, queues: dict):
        self.config = config
        self.queues = queues
        super().__init__()
        self.daemon = True

    def run(self):
        LOG.info("Calculator running on PID %d", os.getpid())
        # TODO calc features here and push down to subs
