#!/bin/bash

# TODO this script is invoked from python and expects single json string output hence no extra echoes

if ! [[ -n "$1" ]]; then
  echo "Need to pass dag name"
  exit 0
fi
dags_path="/opt/airflow/dags"
namespace="airflow"
dag_name="$1"
worker_pod="airflow-worker-0"

# get scheduler pod name
scheduler_pod=$(kubectl get pods  -l component=scheduler -n $namespace -o=jsonpath='{range .items..metadata}{.name}{"\n"}{end}')

kubectl cp "${dag_name}" "${namespace}/${worker_pod}:${dags_path}/${dag_name}"
echo "Copied to ${worker_pod}"
kubectl cp "${dag_name}" "${namespace}/${scheduler_pod}:${dags_path}/${dag_name}"
echo "Copied to ${scheduler_pod}"