#!/bin/bash

kubectl delete secret regcred
kubectl create secret docker-registry regcred \
  --docker-server=050011372339.dkr.ecr.ap-northeast-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password) \
  --namespace=data-feed