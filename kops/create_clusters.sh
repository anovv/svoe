#!/bin/bash

TF_OUTPUT_JSON=$(cd ../terraform && terraform output -json)
MULTICLUSTER_CONFIG=$(echo $TF_OUTPUT_JSON | jq -r .multicluster_config_output.value)
while read cluster_id; do
  cluster_conf=$(echo $TF_OUTPUT_JSON | jq -r .multicluster_config_output.value.$cluster_id)
  cluster_name=$(echo $cluster_conf | jq -r .cluster_name)
  cluster_id=$(echo "$cluster_id" | tr -d '"') # remove quotes
  ./_create_cluster.sh $cluster_id | sed -e "s/^/[${cluster_name}] /" &
done <<< "$(echo $MULTICLUSTER_CONFIG | jq 'to_entries[] | .key')"
wait
echo "All clusters are created."