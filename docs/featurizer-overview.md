# Featurizer

## Overview

## Key features

- Flexible computation model: define modular FeatureDefinition’s to calculate features on historical data as well as live data streams using the same code
- High configurability: Define yaml configs to produce feature sets/feature-label sets for unsupervised/supervised learning and analysis
- Scalable execution: Built on top of Ray, Featurizer allows for horizontally scalable feature calculations on historical data
- Scalable data storage: Unified data model and data access API for time-series data sources and user defined features allows for easy data discovery and retrieval
- Zero-copy in-memory data access : Featurizer integrates with Ray’s distributed in-memory storage, allowing to use Ray’s distributed ML frameworks (XGBoost, PyTorch, RLLib) for predictive modelling without moving data to the third party storage