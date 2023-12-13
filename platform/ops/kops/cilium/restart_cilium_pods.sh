#!/bin/bash

if ! [[ -n "$1" ]]; then
  echo "Cluster id is not set"
  exit
fi
CLUSTER_ID="\"$1\""
TF_OUTPUT_JSON=$(cd ../../terraform && terraform output -json) # TODO use relative paths
CLUSTER_CONFIG=$(echo $TF_OUTPUT_JSON | jq -r .multicluster_config_output.value.$CLUSTER_ID)
CLUSTER_NAME=$(echo $CLUSTER_CONFIG | jq -r .cluster_name)

kubectl config use-context $CLUSTER_NAME
kubectl delete pod -l k8s-app=etcd-manager-cilium -n kube-system
kubectl delete pod -l k8s-app=clustermesh-apiserver -n kube-system
kubectl delete pod -l io.cilium/app -n kube-system
kubectl delete pod -l k8s-app=cilium -n kube-system