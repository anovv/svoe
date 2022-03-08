#!/bin/bash -e

if [ -z "$MYSQL_S3_INIT" ]; then
  echo "[$(date -Iseconds)] Mysqls3dumper already inited"
else
  echo "[$(date -Iseconds)] Mysqls3dumper init..."
  apk --update add mysql-client bash python3 && pip3 install awscli
  if [ $? -eq 0 ]; then
    export MYSQL_S3_INIT=true
    echo "[$(date -Iseconds)] Done"
  fi
fi