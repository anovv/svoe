#!/bin/bash

minikube start --nodes 3 --extra-config=kubelet.housekeeping-interval=10s -p minikube-1
./install_provisioner.sh
./label_nodes.sh