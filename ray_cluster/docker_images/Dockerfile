FROM rayproject/ray:2.4.0-py39-cpu
RUN sudo apt-get update
RUN sudo apt-get -y install gcc
COPY reqs.txt /opt/svoe/reqs.txt
RUN pip install -r /opt/svoe/reqs.txt