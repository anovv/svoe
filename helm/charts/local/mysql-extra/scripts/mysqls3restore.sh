#!/bin/sh -e

# TODO figure out users/priviliges

MYSQL_S3_INITED_FLAG_FILE=/tmp/mysql_s3_is.inited
echo "[$(date -Iseconds)] Started mysql restore from s3"

if ! [ -f "$MYSQL_S3_INITED_FLAG_FILE" ]; then
  echo "[$(date -Iseconds)] mysqls3 is not inited, exiting"
  return 0
fi

s3filename_latest="mysqldump_latest.sql.gz"
s3filename_latest_unzip="mysqldump_latest.sql"
aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename_latest} || not_exist=true
if [ $not_exist ]; then
  echo "[$(date -Iseconds)] No backup file in s3, exiting"
  set +e
  SUCCESS=false
  while [ "$SUCCESS" = false ]
  do
    echo "[$(date -Iseconds)] Creating db ..."
    mysql -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_ROOT_USER}" -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE};"
    if [ $? -eq 0 ]; then
      SUCCESS=true
    else
      echo "[$(date -Iseconds)] Failed creating db. Retrying in 30s..."
      sleep 30
    fi
  done
  return 0
else
  echo "[$(date -Iseconds)] Started downloading..."
  aws s3 cp "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}" "${s3filename_latest}"
  echo "[$(date -Iseconds)] Backup downloaded. Unzipping..."
  gzip -d -f "${s3filename_latest}"
  echo "[$(date -Iseconds)] Unzip finished. Restoring mysql..."
  set +e
  SUCCESS=false
  while [ "$SUCCESS" = false ]
  do
    echo "[$(date -Iseconds)] Restoring dump file"
    # https://stackoverflow.com/questions/14011968/user-cant-access-a-database
    mysql -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_ROOT_USER}"  -p"${MYSQL_ROOT_PASSWORD}" < "${s3filename_latest_unzip}"
    if [ $? -eq 0 ]; then
      SUCCESS=true
    else
      echo "[$(date -Iseconds)] Failed restoring dump file. Retrying in 30s..."
      sleep 30
    fi
  done
  rm -rf "${s3filename_latest_unzip}"
fi
echo "[$(date -Iseconds)] Done."

