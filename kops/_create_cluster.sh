#!/bin/bash

if ! [[ -n "$1" ]]; then
  echo "Cluster id is not set"
  exit
fi
CLUSTER_ID="\"$1\""
TF_OUTPUT_JSON=$(cd ../terraform && terraform output -json)
CLUSTER_CONFIG=$(echo $TF_OUTPUT_JSON | jq -r .multicluster_config_output.value.$CLUSTER_ID)
CLUSTER_NAME=$(echo $CLUSTER_CONFIG | jq -r .cluster_name)
OUTPUT_PATH="clusters/${CLUSTER_NAME}"
TERRAFORM_OUTPUT_PATH="${OUTPUT_PATH}/terraform/"

./_gen_cluster_config.sh $1

cd $TERRAFORM_OUTPUT_PATH
terraform init
terraform apply --auto-approve
# TODO kops export config
echo "Cluster creation done"