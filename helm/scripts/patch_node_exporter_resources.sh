#!/bin/bash

kubectl patch daemonset kube-prometheus-stack-prometheus-node-exporter -n monitoring -p '{"spec":{"template":{"spec":{"containers":[{"resources":{"limits":{"memory":"50Mi", "cpu": "30m"}, "requests":{"memory":"50Mi", "cpu": "30m"}},"name":"node-exporter"}]}}}}'