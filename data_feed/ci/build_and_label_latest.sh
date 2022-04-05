#!/bin/bash

# TODO move these to terraform config?
SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME="svoe_data_feed_prod"

cd ../../../cryptofeed # TODO set up proper paths
# make sure cryptofeed local and remote branches are synced
# look out if they rename it 'master' -> 'main'
diff=$(git diff master origin/master)
if ! [ -z $diff ]; then
  echo "Cryptofeed fork local and remote are not synced, exiting."
  exit 0
fi
echo "Cryptofeed fork local and remote are synced..."
cryptofeed_last_commit_hash=$(git rev-parse --short HEAD)
cryptofeed_latest_tag=$(git tag -l | tail -n 1)

# make sure cryptostore local and remote branches are synced
cd ../cryptostore # TODO set up proper paths
diff=$(git diff master origin/master)
if ! [ -z $diff ]; then
  echo "Cryptostore fork local and remote are not synced, exiting."
  exit 0
fi
echo "Cryptostore fork local and remote are synced..."

cryptostore_last_commit_hash=$(git rev-parse --short HEAD)
cryptostore_latest_tag=$(git tag -l | tail -n 1)

cd ../svoe  # TODO set up proper paths
svoe_last_commit_hash=$(git rev-parse --short HEAD)

echo "cryptofeed-latest-tag=${cryptofeed_latest_tag}"
echo "cryptofeed-last-commit-hash-latest-tag=${cryptofeed_last_commit_hash}"
echo "cryptostore-latest-tag=${cryptostore_latest_tag}"
echo "cryptostore-last-commit-hash=${cryptostore_last_commit_hash}"
echo "svoe-last-commit-hash=${svoe_last_commit_hash}"

cd data_feed # TODO set up proper paths
echo "Building image ${SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME}:latest..."
docker build . -f Dockerfile -t ${SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME}:latest  \
  --label "cryptofeed-latest-tag=${cryptofeed_latest_tag}" \
  --label "cryptofeed-last-commit-hash-latest-tag=${cryptofeed_last_commit_hash}" \
  --label "cryptostore-latest-tag=${cryptostore_latest_tag}" \
  --label "cryptostore-last-commit-hash=${cryptostore_last_commit_hash}" \
  --label "svoe-last-commit-hash=${svoe_last_commit_hash}"

echo "Done."