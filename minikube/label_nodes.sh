#!/bin/bash

kubectl label nodes minikube-1-m02 workload-type=data-feed
kubectl label nodes minikube-1-m02 node-type=spot