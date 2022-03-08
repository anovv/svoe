#!/bin/sh -e

# should be used inside ubuntu images (mysql image is ubuntu)
# https://iamvickyav.medium.com/mysql-init-script-on-docker-compose-e53677102e48
if [ -z "$MYSQL_S3_INIT" ]; then
  echo "[$(date -Iseconds)] Mysqls3 init..."
  apt-get -y update && apt-get -y dist-upgrade && apt-get -y install mysql-client python3 python3-pip && pip3 install awscli
  export MYSQL_S3_INIT=true
  echo "[$(date -Iseconds)] Done"
else
  echo "[$(date -Iseconds)] Mysqls3 already inited"
fi