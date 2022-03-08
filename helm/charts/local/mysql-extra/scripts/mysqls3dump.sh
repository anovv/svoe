#!/bin/sh -e
# TODO possible race condition since this script can be called from different pods
filename=$(mktemp)
echo "[$(date -Iseconds)] Started mysqldump"

if [ -z "$MYSQL_DATABASE" ]; then
	MYSQL_DATABASE="--all-databases"
else
	MYSQL_DATABASE="--databases ${MYSQL_DATABASE}"
fi

mysqldump --no-tablespaces -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} > "${filename}"
echo "[$(date -Iseconds)] mysqldump finished. Started compression"
gzip "${filename}"
echo "[$(date -Iseconds)] Compression finished"

s3filename_latest="mysqldump_latest.sql.gz"
s3filename_prev="mysqldump_prev.sql.gz"
echo "[$(date -Iseconds)] Started s3 upload"
aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename_prev} || prev_not_exist=true
if [ $prev_not_exist ]; then
  echo "[$(date -Iseconds)] Prev version does not exist"
else
  # TODO it never goes here...
  aws s3api head-object --bucket ${AWS_S3_MYSQL_BUCKET} --key ${s3filename_latest} || latest_not_exist=true
  if [ $latest_not_exist ]; then
    echo "[$(date -Iseconds)] Latest version does not exist, but prev exists, shouldn't happen..."
  else
    aws s3 rm "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_prev}"
    echo "[$(date -Iseconds)] Removed current prev"
    aws s3 mv "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}" "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_prev}"
    echo "[$(date -Iseconds)] Moved latest version to prev"
    aws s3 rm "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_prev}"
    echo "[$(date -Iseconds)] Removed current latest"
  fi
fi
aws s3 cp "${filename}.gz" "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename_latest}"
echo "[$(date -Iseconds)] Uploaded new latest"
rm -rf "${filename}.gz"
echo "[$(date -Iseconds)] Done"