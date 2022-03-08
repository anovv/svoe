#!/bin/bash -e

echo "[$(date -Iseconds)] Started mysql restore from s3"
if [ -z "$MYSQL_DATABASE" ]; then
	MYSQL_DATABASE="--all-databases"
else
	MYSQL_DATABASE="--databases ${MYSQL_DATABASE}"
fi
s3filename_latest="mysqldump_latest.sql.gz"
s3filename_latest_unzip="mysqldump_latest.sql"
aws s3api head-object --bucket ${AWS_S3_BUCKET} --key ${s3filename_latest} || not_exist=true
if [ $not_exist ]; then
  echo "[$(date -Iseconds)] No backup file in s3"
else
  echo "[$(date -Iseconds)] Started downloading..."
  aws s3 cp "s3://${AWS_S3_BUCKET}/${s3filename_latest}" "${s3filename_latest}"
  echo "[$(date -Iseconds)] Backup downloaded. Unzipping..."
  gzip -d "${s3filename_latest}"
  echo "[$(date -Iseconds)] Unzip finished. Restoring mysql..."
  mysql -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_USER}" -p "${MYSQL_PASSWORD}" ${MYSQL_DATABASE} < "${s3filename_latest_unzip}"
  rm -rf "${s3filename_latest_unzip}"
fi
echo "[$(date -Iseconds)] Done"