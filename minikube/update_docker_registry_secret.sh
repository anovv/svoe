#!/bin/bash

# TODO use helm chart instead if this is also required for prod/dev remote clusters
# https://artifacthub.io/packages/helm/architectminds/aws-ecr-credential
# https://artifacthub.io/packages/helm/zbytes/ecr-creds for multi ns
kubectl create namespace data-feed
kubectl delete secret regcred --namespace=data-feed
kubectl create secret docker-registry regcred \
  --docker-server=050011372339.dkr.ecr.ap-northeast-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password) \
  --namespace=data-feed