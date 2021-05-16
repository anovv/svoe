FROM python:3.9.4-buster

WORKDIR /usr/src/svoe/data_feed
COPY . .

RUN apt install gcc git

RUN pip install --no-cache-dir git+https://github.com/bmoscon/cryptostore.git

RUN pip install boto3

RUN pip install -e .

ENTRYPOINT ["svoe_data_feed_launch"]
