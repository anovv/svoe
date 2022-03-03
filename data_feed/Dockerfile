# TODO try -slim, faster pip install
FROM python:3.9.4-buster

RUN mkdir -p /etc/svoe/data_feed/configs
COPY data-feed-config.yaml /etc/svoe/data_feed/configs/data-feed-config.yaml

WORKDIR /usr/src/svoe/data_feed
COPY . .

RUN apt install gcc git

RUN pip install --no-cache-dir git+https://github.com/dirtyValera/cryptostore.git # TODO is it pulled twice here and in setup.py ??
RUN pip install --no-cache-dir redis
RUN pip install --no-cache-dir git+https://github.com/aio-libs/aioredis-py@4dfdc05
RUN pip install --no-cache-dir boto3

# TODO figure out if any of packages here are duplicated in setup.py

RUN pip install -e .\[prod\]

ENTRYPOINT ["svoe_data_feed_launch"]
