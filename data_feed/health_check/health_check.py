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

        r = redis.Redis(redis_ip, redis_port)
        if num_redis_keys != len(r.keys()):
            print('[HEALTH CHECK FAILED][Redis]: Keys expected ' + str(num_redis_keys) + ' Keys read ' + str(len(r.keys())))
            sys.exit(FAILURE)

        # verify feednandler.log and cryptostore.log
        storage_interval_seconds = config['storage_interval']
        mtime_feedhandler = os.path.getmtime(FEEDHANDLER_LOG_PATH)
        mtime_cryptostore = os.path.getmtime(CRYPTOSTORE_LOG_PATH)
        now = time.time()
        fh_delta = now - mtime_feedhandler
        cs_delta = now - mtime_cryptostore

        if fh_delta > storage_interval_seconds + 2:
            print('[HEALTH CHECK FAILED][Feedhandler]: Log was updated ' + str(fh_delta) + ' seconds ago')
            sys.exit(FAILURE)

        if cs_delta > storage_interval_seconds + 2:
            print('[HEALTH CHECK FAILED][Cryptostore]: Log was updated ' + str(cs_delta) + ' seconds ago')
            sys.exit(FAILURE)

        sys.exit(SUCCESS)

check()