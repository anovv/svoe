# Trainer

## Overview

## Key features

- Highly configurable: Trainer provides unified API and configs to train and evaluate predictive models using various ML libraries (XGBoost, PyTorch, RLLib)
- Integrated with Featurizer: Use distributed in-memory FeatureLabelSet data structure to train your predictive models without extra data pipelines
- Scalability: Data-parallel distributed training for all supported frameworks
- Hyperparameter optimization: Use Ray Tune to optimize hyperparameters and pick the best model
- Model and metadata storage: Trainer provides easy API for model access and metadata discovery by integrating with MLFlow