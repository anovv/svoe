#!/bin/bash

mkdir -p /tmp/svoe/mlflow/mlruns/
mlflow server --backend-store-uri=sqlite:////tmp/svoe/sqlite/svoe_db.db --default-artifact-root=file:/tmp/svoe/mlflow/mlruns
