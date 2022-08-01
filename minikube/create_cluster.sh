#!/bin/bash

minikube config set memory 3072 # need to shutdown docker desktop for this to work
minikube start --nodes 2 --extra-config=kubelet.housekeeping-interval=10s -p minikube-1

# memory overcommit configuration
#kubectl node-shell minikube-1-m02 -- bash -c "echo 2 > /proc/sys/vm/overcommit_memory && echo 100 > /proc/sys/vm/overcommit_ratio"

# label nodes
kubectl label nodes minikube-1-m02 workload-type=data-feed
kubectl label nodes minikube-1-m02 node-type=spot
kubectl label nodes minikube-1-m02 svoe-role=resource-estimator

# taints
kubectl taint nodes minikube-1-m02 node-type=spot:NoSchedule
kubectl taint nodes minikube-1-m02 workload-type=data-feed:NoSchedule
kubectl taint nodes minikube-1-m02 svoe-role=resource-estimator:NoSchedule

# patch kube-proxy to be QoS Guaranteed
kubectl patch daemonset kube-proxy -n kube-system -p '{"spec":{"template":{"spec":{"containers":[{"resources":{"limits":{"memory":"50Mi", "cpu": "40m"}, "requests":{"memory":"50Mi", "cpu": "40m"}},"name":"kube-proxy"}]}}}}'

# install volume provisioner
curl https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml | sed 's/\/opt\/local-path-provisioner/\/var\/opt\/local-path-provisioner/ ' | kubectl apply -f -
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# auth for ecr docker registry
./update_docker_registry_secret.sh

# TODO cilium pods take some time to spin up, wait for them?