#!/bin/bash

minikube start --nodes 3 -p minikube-1
./install_provisioner.sh
./label_nodes.sh