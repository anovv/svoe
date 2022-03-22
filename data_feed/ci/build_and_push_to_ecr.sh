#!/bin/bash

TF_OUTPUT_JSON=$(cd ../../terraform && terraform output -json)
ECR_REPO_URL=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_url.value)
ECR_REGISTRY_ID=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_registry_id.value)
ECR_REPO_NAME=$(echo $TF_OUTPUT_JSON | jq -r .svoe_data_feed_ecr_repo_name.value)

aws ecr list-images --registry-id $ECR_REGISTRY_ID --repository-name $ECR_REPO_NAME