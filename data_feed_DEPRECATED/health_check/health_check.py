# Script to be called by Kubernetes liveness probe

import yaml
import redis
import os
import time
import sys

# TODO this path should be synced with cryptostore_config_builder consts
DATA_FEED_CONFIG_PATH = '/etc/svoe/data_feed/configs/data-feed-config.yaml'
CRYPTOSTORE_LOG_PATH = 'cryptostore.log'
FEEDHANDLER_LOG_PATH = 'feedhandler.log'

SUCCESS = 0
FAILURE = 1

def tail(filename, n=10):
    from collections import deque
    return ''.join(deque(open(filename), n))

def check():
    # read config
    with open(DATA_FEED_CONFIG_PATH) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

        # verify redis
        redis_ip = config['redis']['ip']
        redis_port = config['redis']['port']
        # number of redis keys should be equal to num channels (ticker, trades, l2, l3) * num symbols
        # count number of keys
        num_redis_keys = 0
        exchanges = config['exchanges']
        for exchnage in exchanges:
            ex_conf = exchanges[exchnage]
            if 'trades' in ex_conf:
                num_redis_keys += len(ex_conf['trades'])

            if 'ticker' in ex_conf:
                num_redis_keys += len(ex_conf['ticker'])

            if 'l2_book' in ex_conf:
                num_redis_keys += len(ex_conf['l2_book']['symbols'])

            if 'l3_book' in ex_conf:
                num_redis_keys += len(ex_conf['l3_book']['symbols'])

            if 'liquidations' in ex_conf:
                num_redis_keys += len(ex_conf['liquidations']['symbols'])

            if 'open_interest' in ex_conf:
                num_redis_keys += len(ex_conf['open_interest']['symbols'])

            if 'funding' in ex_conf:
                num_redis_keys += len(ex_conf['funding']['symbols'])


        r = redis.Redis(redis_ip, redis_port)
        keys = r.keys()
        if num_redis_keys != len(keys):
            print('[HEALTH CHECK][FAILED][Redis]: Keys expected ' + str(num_redis_keys) + ' Keys read ' + str(len(keys)))
            print('[HEALTH CHECK][feedhandler.log tail]:\n' + tail(FEEDHANDLER_LOG_PATH))
            print('[HEALTH CHECK][cryptostore.log tail]:\n' + tail(CRYPTOSTORE_LOG_PATH))
            sys.exit(FAILURE)

        # verify cryptostore.log
        storage_interval_seconds = config['storage_interval']
        mtime_cryptostore = os.path.getmtime(CRYPTOSTORE_LOG_PATH)
        now = time.time()
        cs_delta = now - mtime_cryptostore

        if cs_delta > storage_interval_seconds + 2:
            print('[HEALTH CHECK][FAILED][Cryptostore]: Log was updated ' + str(cs_delta) + ' seconds ago')
            print('[HEALTH CHECK][feedhandler.log tail]:\n' + tail(FEEDHANDLER_LOG_PATH))
            print('[HEALTH CHECK][cryptostore.log tail]:\n' + tail(CRYPTOSTORE_LOG_PATH))
            sys.exit(FAILURE)

        sys.exit(SUCCESS)

check()
