#!/bin/sh -e

# TODO posibility of race since this can be called from different pods
# TODO figure out users/priviliges

MYSQL_S3_INITED_FLAG_FILE=/tmp/mysql_s3_is.inited
echo "[$(date -Iseconds)] Started mysql s3 dump..."

if ! [ -f "$MYSQL_S3_INITED_FLAG_FILE" ]; then
  echo "[$(date -Iseconds)] mysqls3 is not inited, exiting"
  return 0
else
  echo "[$(date -Iseconds)] mysqls3 is already inited"
fi

filename=$(mktemp)
db_name_prefix=""

if [ -z "$MYSQL_DATABASE" ]; then
  db_name_prefix="all-dbs"
  MYSQL_DATABASE="--all-databases"
else
  db_name_prefix=${MYSQL_DATABASE}
  MYSQL_DATABASE="--databases ${MYSQL_DATABASE}"
fi

echo "[$(date -Iseconds)] Calling mysqldump..."
mysqldump --no-tablespaces -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u root -p"${MYSQL_ROOT_PASSWORD}" ${MYSQL_DATABASE} > "${filename}"
echo "[$(date -Iseconds)] mysqldump finished. Started compression..."
gzip "${filename}"
echo "[$(date -Iseconds)] Compression finished"

s3filename_latest="${db_name_prefix}_mysqldump_latest.sql.gz"
s3filename_prev="${db_name_prefix}_mysqldump_prev.sql.gz"
echo "[$(date -Iseconds)] Started s3 upload..."

aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename_latest} || latest_not_exist=true
if [ $latest_not_exist ]; then
  echo "[$(date -Iseconds)] Latest version does not exist..."
  aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename_prev} || prev_not_exist=true
  if [ $prev_not_exist ]; then
    echo "[$(date -Iseconds)] Prev version does not exist, first upload, uploading new latest.."
    aws s3 cp "${filename}.gz" "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}"
  else
    echo "[$(date -Iseconds)] Latest version does not exist, but prev exists, shouldn't happen, exiting"
    return 0
  fi
else
  echo "[$(date -Iseconds)] Found existing latest..."
  aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename_prev} || prev_not_exist=true
  if [ $prev_not_exist ]; then
    echo "[$(date -Iseconds)] Prev version does not exist..."
  else
    echo "[$(date -Iseconds)] Prev version found, removing..."
    aws s3 rm "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_prev}"
  fi
  echo "[$(date -Iseconds)] Moving latest to prev..."
  aws s3 mv "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}" "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_prev}"
  echo "[$(date -Iseconds)] Removing current latest..."
  aws s3 rm "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}"
  echo "[$(date -Iseconds)] Uploading new latest..."
  aws s3 cp "${filename}.gz" "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}"
fi
rm -rf "${filename}.gz"
echo "[$(date -Iseconds)] Done."
# TODO indicate failure in container
