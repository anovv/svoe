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
mkdir -p $OUTPUT_PATH
VALUES_OUTPUT_PATH="${OUTPUT_PATH}/values.yaml"
KOPS_CLUSTER_CONFIG_OUPUT_PATH="${OUTPUT_PATH}/cluster.yaml"
TEMPLATE_PATH="template.yaml"
TERRAFORM_OUTPUT_PATH="${OUTPUT_PATH}/terraform/"
mkdir -p $TERRAFORM_OUTPUT_PATH

(echo $CLUSTER_CONFIG | yq e -P -) > $VALUES_OUTPUT_PATH

echo "Cluster ${CLUSTER_NAME} id ${CLUSTER_ID}"
echo "Terraform input values in ${VALUES_OUTPUT_PATH}"

kops delete cluster --state $STATE --name $CLUSTER_NAME --yes
echo "Cleared old state at "$STATE

kops toolbox template --name ${CLUSTER_NAME} --values ${VALUES_OUTPUT_PATH} --template ${TEMPLATE_PATH} --format-yaml > ${KOPS_CLUSTER_CONFIG_OUPUT_PATH}
echo "Kops cluster config in ${KOPS_CLUSTER_CONFIG_OUPUT_PATH}"

kops replace -f ${KOPS_CLUSTER_CONFIG_OUPUT_PATH} --state $STATE --name $CLUSTER_NAME --force
echo "Kops state moved to "$STATE

kops create secret --name $CLUSTER_NAME --state $STATE --name $CLUSTER_NAME sshpublickey admin -i ~/.ssh/id_rsa.pub
echo "Created secret sshpublickey"

kops update cluster --out=$TERRAFORM_OUTPUT_PATH --target=terraform --state $STATE --name $CLUSTER_NAME
echo "Terraform output in ${TERRAFORM_OUTPUT_PATH}"
echo "Done."