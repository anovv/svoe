#!/bin/bash

# TODO move these to terraform config?
# manually increase on each push
# update changelog
LATEST_VERSION="1.0.2"
SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME="svoe_data_feed_prod"
LATEST_VERSION_TAG="v${LATEST_VERSION}"

TF_OUTPUT_JSON=$(cd ../../terraform && terraform output -json)
ECR_REPO_URL=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_url.value)
ECR_REGISTRY_ID=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_registry_id.value)
ECR_REPO_NAME=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_name.value)

# check if latest version is already in ECR
IMAGE_TAGS=$(aws ecr describe-images --registry-id $ECR_REGISTRY_ID --repository-name $ECR_REPO_NAME --output json | jq -r ".imageDetails[].imageTags")
LATEST_INDEX=$(echo $IMAGE_TAGS | jq -s "flatten | index([\"${LATEST_VERSION_TAG}\"])")
if ! [ $LATEST_INDEX = null ]; then
  echo "Version ${LATEST_VERSION_TAG} is already in ECR, exiting."
  exit 0
else
  echo "Version ${LATEST_VERSION_TAG} is not in ECR ..."
fi

# get latest image id from local docker registry
echo "Locating ${SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME}:latest local docker image id ..."
LATEST_IMAGE_IDS=$(docker images "${SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME}:latest" | awk '{print $3}' | tail -n +2)
if ! [ ${#LATEST_IMAGE_IDS[@]} = 1 ]; then
  echo "Found multiple image ids ${LATEST_IMAGE_IDS} for ${SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME}:latest, exiting."
  exit 0
else
  echo "Local image id ${LATEST_IMAGE_IDS[0]} ..."
fi

echo "Tagging ${SVOE_DATA_FEED_PROD_LOCAL_DOCKER_IMAGE_NAME}:latest local docker image id ..."
docker tag ${LATEST_IMAGE_IDS[0]} ${ECR_REPO_URL}:${LATEST_VERSION_TAG}
echo "Tagged: ${ECR_REPO_URL}:${LATEST_VERSION_TAG}"

echo "Getting ECR login for registry id ${ECR_REGISTRY_ID} and docker login ..."
aws ecr get-login-password | docker login --username AWS --password-stdin ${ECR_REPO_URL}

echo "Pushing ${ECR_REPO_URL}:${LATEST_VERSION_TAG} to ECR ..."
docker push "${ECR_REPO_URL}:${LATEST_VERSION_TAG}"

echo "Done."