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
STATE="s3://$(echo $CLUSTER_CONFIG | jq -r .kops_s3_bucket_name)"

./_gen_cluster_config.sh $1

cd $TERRAFORM_OUTPUT_PATH
#terraform init -upgrade TODO only with VPN
terraform apply --auto-approve
kops export kubeconfig --admin --name $CLUSTER_NAME --state $STATE
echo "Cluster creation done"