FROM python:3.9.4-buster

RUN mkdir -p /etc/svoe/data_feed/configs
COPY data-feed-config.yaml /etc/svoe/data_feed/configs/data-feed-config.yaml

WORKDIR /usr/src/svoe/data_feed
COPY . .

RUN apt install gcc git

RUN pip install --no-cache-dir git+https://github.com/bmoscon/cryptostore.git
RUN pip install --no-cache-dir redis
RUN pip install --no-cache-dir git+https://github.com/aio-libs/aioredis-py@4dfdc05
RUN pip install --no-cache-dir boto3

RUN pip install -e .

ENTRYPOINT ["svoe_data_feed_launch"]
