# should be built from root dir

FROM apache/airflow:latest-python3.10
COPY ./ray_cluster/docker_images/reqs.txt /opt/svoe/reqs.txt
USER root
RUN apt-get update
RUN apt-get -y install gcc
USER airflow
ENV SLUGIFY_USES_TEXT_UNIDECODE=yes
RUN pip install -r /opt/svoe/reqs.txt
RUN pip install dag-factory --no-deps apache-airflow
COPY svoe_airflow/gen_dag.py /opt/airflow/dags/gen_dag.py

# copy local packages
# TODO package it in a better way
COPY ./client /svoe_deps/client
COPY ./common /svoe_deps/common
COPY ./featurizer /svoe_deps/featurizer
COPY ./ray_cluster /svoe_deps/ray_cluster
COPY ./simulation /svoe_deps/simulation
COPY ./svoe_airflow /svoe_deps/svoe_airflow
COPY ./trainer /svoe_deps/trainer
COPY ./utils /svoe_deps/utils

ENV PYTHONPATH "${PYTHONPATH}:/svoe_deps/"