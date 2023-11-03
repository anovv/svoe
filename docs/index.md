# Overview

A low-code framework providing scalable and highly configurable pipelines for financial data research, streaming and batch feature engineering, predictive model training, real-time inference and backtesting. Built on top of Ray, the framework allows to build and scale your custom pipelines from multi-core laptop to a cluster of 1000s of nodes.

## Why use Svoe?

- Easy to use standardized and flexible data and computation models
- Low code, modularity and configurability
- Ray integration
- Cloud / Kubernetes ready
- Easily integrated with orchestrators (Airflow, Luidgi, Prefect, etc.)
- Designed for high volume low granularity data (tick data)
- Minimized number of third party dependecndy - no external storages, stream processors and other heavy weight systems

## Components

* `svoe featurizer` - Featurizer.
* `svoe trainer` - Trainer.
* `svoe backtester` - Backtester.
* `svoe -h` - Print help message and exit.