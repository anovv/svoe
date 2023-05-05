import logging
from logging.handlers import RotatingFileHandler


FORMAT = logging.Formatter('%(asctime)-15s : %(levelname)s : %(message)s')


# TODO unify logging for cryptostore/cryptofeed/data_feed/featurizer
def get_logger(name, filename, level=logging.WARNING, size=200000, num_files=5):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    stream = logging.StreamHandler()
    stream.setFormatter(FORMAT)
    logger.addHandler(stream)

    fh = RotatingFileHandler(filename, maxBytes=size, backupCount=num_files)
    fh.setFormatter(FORMAT)
    logger.addHandler(fh)
    logger.propagate = False
    return logger
