# Featurizer

## Overview

Featurizer is a framework combining stream/batch feature processing engine, feature storage, exploration API and user facing
SDKs and configs to define features for real-time and batch (historical) processing.

Featurizer is built around a custom stream processing engine (built on top of Ray Actors and ZeroMQ)
and uses Kappa-architecture to calculate offline features using online pipelines.

Featurizer leverages Ray's distributed memory to produce feature sets/feature-label sets for
ML training without having costly data transfers.

## Key features

- Flexible computation model: define modular FeatureDefinition’s to calculate features on historical data as well as live data streams using the same code
- High configurability: Define yaml configs to produce feature sets/feature-label sets for unsupervised/supervised learning and analysis
- Scalable execution: Built on top of Ray, Featurizer allows for horizontally scalable stream processing and feature calculations on historical data
- Scalable data storage: Unified data model and data access API for time-series data sources and user defined features allows for easy data discovery and retrieval
- Zero-copy in-memory data access: Featurizer integrates with Ray’s distributed in-memory storage, allowing to use Ray’s distributed ML frameworks (XGBoost, PyTorch, RLLib) for predictive modelling without moving data to the third party storage

## How is it different from other stream processors (Flink, Spark Streaming)?

The main goal of our framework is to provide a standalone real-time ML solution by reducing typical heavyweight dependencies
which are present in similar systems - mainly Flink and Spark. Featurizer uses custom stream
processing engine which is built on top of Ray Actors - this gives Kubernetes-ready system, helps to avoid cloud/vendor lock-in, 
provides a common platform for feature processing and ML training/inference and as a result eliminates such problems as 
heavyweight data transfers, CI/CD pipeline-hell and boilerplate inference code (FastAPI/Docker wrappers).

Current version of Featurizer is built using Streamz Python library for pipeline definitions and 
has a limited functionality, but our main focus is to provide full feature parity with Flink (state backend, checkpoints,
watermarks, joins/shuffles, elasticity/autoscaling, etc.)