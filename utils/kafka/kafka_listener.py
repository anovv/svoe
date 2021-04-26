from confluent_kafka import Consumer, KafkaError, KafkaException
import sys

GROUP_ID = 'svoe_kafka_handler'
TOPIC = 'ticker-COINBASE-BTC-USD'

running = True

class KafkaListener:

    def handle_message(self):
        conf = {'bootstrap.servers': 'localhost:9092',
                'group.id': GROUP_ID,
                'auto.offset.reset': 'smallest'}

        consumer = Consumer(conf)
        try:
            consumer.subscribe([TOPIC])

            while running:
                msg = consumer.poll(timeout=5)
                if msg is None:
                    print("msg non")
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition event
                        sys.stderr.write('%% %s [%d] reached end at offset %d\n' %
                                         (msg.topic(), msg.partition(), msg.offset()))
                    elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        # TODO add error message
                        # TODO sleep here
                        print("no topic")
                    elif msg.error():
                        raise KafkaException(msg.error())
                else:
                    print(msg.value())
        finally:
            # Close down consumer to commit final offsets.
            consumer.close()

    def shutdown(self):
        running = False
