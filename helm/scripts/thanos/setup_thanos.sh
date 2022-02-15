#!/bin/bash

if ! [[ -n "$1" ]]; then
  echo "Cluster name is not set"
  exit 5
fi

if ! [[ -n "$2" ]]; then
  echo "Namespace is not set"
  exit 5
fi

CLUSTER_NAME=$1
NAMESPACE=$2

DIR="$(dirname "$(which "$0")")"
TEMPLATE_THANOS=$DIR/thanos-objstore-config.yaml
TEMP_THANOS=$DIR/thanos-objstore-config-temp.yaml

#gen temp file with aws key/secrets
# TODO when running from helmfile hook env vars are not visible??
sed -e "s/\${KEY}/${AWS_KEY}/" -e "s/\${SECRET}/${AWS_SECRET}/" $TEMPLATE_THANOS | tee $TEMP_THANOS
echo "Generated temp file with thanos secret"

kubectl create namespace $NAMESPACE --context $CLUSTER_NAME

# remove old secret
kubectl delete secret thanos-objstore-config -n $NAMESPACE --context $CLUSTER_NAME

kubectl -n $NAMESPACE create secret generic thanos-objstore-config --from-file=thanos-objstore-config.yaml=$TEMP_THANOS --context $CLUSTER_NAME
echo "Created secret"

rm $TEMP_THANOS
echo "Removed temp file with secret"