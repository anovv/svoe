FROM python:3.8.2-slim-buster

WORKDIR /usr/src/svoe/data_feed
COPY . .

RUN apt-get update && \
    apt-get -y install gcc git

# TODO move pip dependencies here with --no-cache-dir?
# TODO specify stable branch/commit
RUN pip install --no-cache-dir --default-timeout=300 git+https://github.com/dirtyValera/cryptofeed.git
 # TODO specify stable branch/commit
RUN pip install --no-cache-dir --default-timeout=300 git+https://github.com/dirtyValera/cryptostore.git
RUN pip install --default-timeout=300 -e .


ENTRYPOINT ["svoe_data_feed_launch"]
