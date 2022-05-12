#!/bin/bash

minikube start --cni=cilium --nodes 3 --extra-config=kubelet.housekeeping-interval=10s -p minikube-1

# install volume provisioner
curl https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml | sed 's/\/opt\/local-path-provisioner/\/var\/opt\/local-path-provisioner/ ' | kubectl apply -f -
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# label nodes
kubectl label nodes minikube-1-m02 workload-type=data-feed
kubectl label nodes minikube-1-m02 node-type=spot

# auth for ecr docker registry
./update_docker_registry_secret.sh