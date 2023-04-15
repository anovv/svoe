FROM rayproject/ray:2.3.1-py310-aarch64
RUN sudo apt-get update
RUN sudo apt-get -y install gcc
COPY reqs.txt /opt/svoe/reqs.txt
RUN pip install -r /opt/svoe/reqs.txt