#!/bin/bash

# set requests/limits for node-exporter
kubectl patch daemonset kube-prometheus-stack-prometheus-node-exporter -n monitoring -p '{"spec":{"template":{"spec":{"containers":[{"resources":{"limits":{"memory":"50Mi", "cpu": "30m"}, "requests":{"memory":"50Mi", "cpu": "30m"}},"name":"node-exporter"}]}}}}'

# set requests/limits for kube-state-metrics
rs_name=$(kubectl get replicaset -l app.kubernetes.io/part-of=kube-state-metrics -n monitoring |  awk '{print $1}' | tail -n +2)
kubectl patch replicaset $rs_name -n monitoring -p '{"spec":{"template":{"spec":{"containers":[{"resources":{"limits":{"memory":"50Mi", "cpu": "30m"}, "requests":{"memory":"50Mi", "cpu": "30m"}},"name":"kube-state-metrics"}]}}}}'

# moved this to helm
#kubectl patch statefulset prometheus-kube-prometheus-stack-prometheus -n monitoring --type=json -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--enable-feature=memory-snapshot-on-shutdown"}]'