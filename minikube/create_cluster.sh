#!/bin/bash

minikube start --nodes 2 --extra-config=kubelet.housekeeping-interval=10s -p minikube-1

# memory overcommit configuration # TODO
#kubectl node-shell minikube-1-m02 -- bash -c "echo 2 > /proc/sys/vm/overcommit_memory && echo 100 > /proc/sys/vm/overcommit_ratio"

# label nodes
kubectl label nodes minikube-1-m02 workload-type=data-feed
kubectl label nodes minikube-1-m02 node-type=spot

# TODO add taints?

# install volume provisioner
curl https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml | sed 's/\/opt\/local-path-provisioner/\/var\/opt\/local-path-provisioner/ ' | kubectl apply -f -
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# auth for ecr docker registry
./update_docker_registry_secret.sh

# TODO cilium pods take some time to spin up, wait for them?