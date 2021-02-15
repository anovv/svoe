from confluent_kafka import Consumer, KafkaError, KafkaException
import sys

import time

EXAMPLE_GROUP_ID = 'cryptofeed-l2_book-COINBASE-BTC-USD'
EXAMPLE_TOPIC = 'l2_book-COINBASE-BTC-USD'

running = True

def handle_l2():
    conf = {'bootstrap.servers': 'localhost:9092',
            'group.id': EXAMPLE_GROUP_ID,
            'auto.offset.reset': 'smallest'}

    consumer = Consumer(conf)
    try:
        consumer.subscribe([EXAMPLE_TOPIC])

        while running:
            msg = consumer.poll(timeout=0.01)
            if msg is None: continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    sys.stderr.write('%% %s [%d] reached end at offset %d\n' %
                                     (msg.topic(), msg.partition(), msg.offset()))
                elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    time.sleep(1)
                    # TODO add error message
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                print(msg)
    finally:
        # Close down consumer to commit final offsets.
        consumer.close()

def shutdown():
    running = False