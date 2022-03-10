#!/bin/sh -e

MYSQL_S3_INITED_FLAG_FILE=/tmp/mysql_s3_is.inited
if ! [ -f "$MYSQL_S3_INITED_FLAG_FILE" ]; then
  echo "[$(date -Iseconds)] Mysqls3 init..."
  apk --update add mysql-client python3 py3-pip && pip3 install awscli
  touch $MYSQL_S3_INITED_FLAG_FILE
  echo "[$(date -Iseconds)] Done"
else
  echo "[$(date -Iseconds)] Mysqls3 already inited"
fi