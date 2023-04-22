#!/bin/sh -e

# TODO figure out users/priviliges

MYSQL_S3_INITED_FLAG_FILE=/tmp/mysql_s3_is.inited
echo "[$(date -Iseconds)] Started mysql restore from s3..."

if ! [ -f "$MYSQL_S3_INITED_FLAG_FILE" ]; then
  echo "[$(date -Iseconds)] mysqls3 is not inited, exiting"
  return 0
fi

if [ -z "$MYSQL_DATABASE" ]; then
  db_name_prefix="all-dbs"
else
  db_name_prefix=${MYSQL_DATABASE}
fi

if [ -z "$CLUSTER_NAME" ]; then
  cluster_name="local"
else
  cluster_name="${CLUSTER_NAME}"
fi

if [ -n "$1" ]; then
  cluster_name="$1"
  echo "[$(date -Iseconds)] Cluster name is set via args"
else
  echo "[$(date -Iseconds)] Cluster name is set via env var"
fi

echo "[$(date -Iseconds)] Restoring for cluster ${cluster_name}"

s3filename="${cluster_name}_${db_name_prefix}_mysqldump.sql.gz"
s3filename_unzip="${cluster_name}_${db_name_prefix}_mysqldump.sql"
aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename} || not_exist=true
if [ $not_exist ]; then
  echo "[$(date -Iseconds)] No backup file in s3, exiting"
  set +e
  SUCCESS=false
  while [ "$SUCCESS" = false ]
  do
    echo "[$(date -Iseconds)] Creating db ..."
    mysql -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u root -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE};"
    if [ $? -eq 0 ]; then
      SUCCESS=true
    else
      echo "[$(date -Iseconds)] Failed creating db. Retrying in 5s..."
      sleep 5
    fi
  done
  return 0
else
  echo "[$(date -Iseconds)] Started downloading..."
  aws s3 cp "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename}" "${s3filename}"
  echo "[$(date -Iseconds)] Backup downloaded. Unzipping..."
  gzip -d -f "${s3filename}"
  echo "[$(date -Iseconds)] Unzip finished. Restoring mysql..."
  set +e
  SUCCESS=false
  while [ "$SUCCESS" = false ]
  do
    echo "[$(date -Iseconds)] Restoring dump file..."
    # https://stackoverflow.com/questions/14011968/user-cant-access-a-database
    mysql -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u root  -p"${MYSQL_ROOT_PASSWORD}" < "${s3filename_unzip}"
    if [ $? -eq 0 ]; then
      SUCCESS=true
    else
      echo "[$(date -Iseconds)] Failed restoring dump file. Retrying in 5s..."
      sleep 5
    fi
  done
  rm -rf "${s3filename_unzip}"
fi
echo "[$(date -Iseconds)] Done."

