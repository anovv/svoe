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


if [ -z "$CLUSTER_NAME" ]; then
  cluster_name="local"
else
  cluster_name="${CLUSTER_NAME}"
fi

echo "[$(date -Iseconds)] Calling mysqldump..."
mysqldump --no-tablespaces -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u root -p"${MYSQL_ROOT_PASSWORD}" ${MYSQL_DATABASE} > "${filename}"
echo "[$(date -Iseconds)] mysqldump finished. Started compression..."
gzip "${filename}"
echo "[$(date -Iseconds)] Compression finished"

s3filename="${cluster_name}_${db_name_prefix}_mysqldump.sql.gz"
echo "[$(date -Iseconds)] Started s3 upload..."
aws s3 cp "${filename}.gz" "s3://${AWS_S3_MYSQL_BUCKET}/${s3filename}"

rm -rf "${filename}.gz"
echo "[$(date -Iseconds)] Done."
