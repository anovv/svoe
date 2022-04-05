#!/bin/bash

if ! [[ -n "$1" ]]; then
  echo "Latest version not set"
  exit 0
fi
LATEST_VERSION="$1"

# TODO move these to terraform config?
LATEST_VERSION_TAG="v${LATEST_VERSION}"

TF_OUTPUT_JSON=$(cd ../../terraform && terraform output -json)
ECR_REPO_URL=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_url.value)
ECR_REGISTRY_ID=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_registry_id.value)
ECR_REPO_NAME=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_name.value)

echo "Getting labels from ECR for ${ECR_REPO_URL}:${LATEST_VERSION_TAG}"

# check if latest version is already in ECR
IMAGE_LABELS=$(aws ecr batch-get-image --registry-id $ECR_REGISTRY_ID --repository-name $ECR_REPO_NAME --image-id imageTag=${ECR_REPO_URL}:${LATEST_VERSION_TAG} --output json | jq -r '.images[].imageManifest' | jq -r '.history[0].v1Compatibility' | jq -r '.config.Labels')
echo $IMAGE_LABELS