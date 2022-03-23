FROM python:3.8.2-slim-buster

RUN mkdir -p /etc/svoe/data_feed/configs
COPY data-feed-config.yaml /etc/svoe/data_feed/configs/data-feed-config.yaml

WORKDIR /usr/src/svoe/data_feed
COPY . .

RUN apt-get update && \
    apt-get -y install gcc git
RUN pip install -e .\[prod\]

# TODO move pip package install here with --no-cache-dir?

ENTRYPOINT ["svoe_data_feed_launch"]
