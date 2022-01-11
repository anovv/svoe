#!/bin/bash

TF_OUTPUT_JSON=$(cd ../terraform && terraform output -json)
(echo $TF_OUTPUT_JSON | yq e -P -) > values.yaml
CLUSTER_NAME="$(echo $TF_OUTPUT_JSON | jq -r .cluster_name.value)"
STATE="s3://$(echo $TF_OUTPUT_JSON | jq -r .kops_s3_bucket_name.value)"

echo "Cluster "$CLUSTER_NAME
echo "Terraform input values in values.yaml"

kops toolbox template --name ${CLUSTER_NAME} --values values.yaml --template template.yaml --format-yaml > cluster.yaml
echo "Cluster config in cluster.yaml"

kops delete cluster --state $STATE --name $CLUSTER_NAME --yes
echo "Cleared old state at "$STATE

kops replace -f cluster.yaml --state $STATE --name $CLUSTER_NAME --force
echo "Kops state moved to "$STATE

kops create secret --name $CLUSTER_NAME --state $STATE --name $CLUSTER_NAME sshpublickey admin -i ~/.ssh/id_rsa.pub
echo "Created secret sshpublickey"

kops update cluster --out=terraform_out --target=terraform --state $STATE --name $CLUSTER_NAME
echo "Terraform output in ./terraform_out"
echo "Done."