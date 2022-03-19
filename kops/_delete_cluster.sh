#!/bin/bash

if ! [[ -n "$1" ]]; then
  echo "Cluster id is not set"
  exit
fi
CLUSTER_ID="\"$1\""
TF_OUTPUT_JSON=$(cd ../terraform && terraform output -json)
CLUSTER_CONFIG=$(echo $TF_OUTPUT_JSON | jq -r .multicluster_config_output.value.$CLUSTER_ID)
CLUSTER_NAME=$(echo $CLUSTER_CONFIG | jq -r .cluster_name)
STATE="s3://$(echo $CLUSTER_CONFIG | jq -r .kops_s3_bucket_name)"
OUTPUT_PATH="clusters/${CLUSTER_NAME}"
TERRAFORM_OUTPUT_PATH="${OUTPUT_PATH}/terraform/"

cd $TERRAFORM_OUTPUT_PATH

# TODO drain worker nodes first for workloads to gracefully shutdown
terraform destroy --auto-approve
kops delete cluster --yes --name $CLUSTER_NAME --state $STATE
echo "Cluster deletion done"